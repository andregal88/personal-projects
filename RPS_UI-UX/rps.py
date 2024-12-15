import cv2
import mediapipe as mp
import random
from collections import deque
import statistics as st
import requests

def place_in_frame(background, overlay, x, y, width, height):
    # Ensure the overlay has an alpha channel
    if overlay.shape[2] == 3:
        overlay = cv2.cvtColor(overlay, cv2.COLOR_BGR2BGRA)

    overlay_h, overlay_w, _ = overlay.shape
    target_aspect = width / height
    overlay_aspect = overlay_w / overlay_h

    # Crop the overlay to fit the target dimensions
    if overlay_aspect > target_aspect:
        new_width = int(target_aspect * overlay_h)
        offset = (overlay_w - new_width) // 2
        overlay_cropped = overlay[:, offset:offset + new_width]
    else:
        new_height = int(overlay_w / target_aspect)
        offset = (overlay_h - new_height) // 2
        overlay_cropped = overlay[offset:offset + new_height, :]

    # Resize the overlay to the target dimensions
    overlay_resized = cv2.resize(overlay_cropped, (width, height))

    # Apply the overlay to the background
    alpha_s = overlay_resized[:, :, 3] / 255.0
    alpha_l = 1.0 - alpha_s

    for c in range(0, 3):
        background[y:y+height, x:x+width, c] = (alpha_s * overlay_resized[:, :, c] +
                                                alpha_l * background[y:y+height, x:x+width, c])
    return background

def add_bot_image(background, bot_images, x, y, width, height):
    bot_image = cv2.imread(random.choice(bot_images), cv2.IMREAD_UNCHANGED)
    if bot_image is None:
        print("Error loading bot image!")
        return background
    return place_in_frame(background, bot_image, x, y, width, height)

def apply_background(image, background_path):
    background = cv2.imread(background_path)
    background = cv2.resize(background, (image.shape[1], image.shape[0]))
    combined = cv2.addWeighted(background, 0.5, image, 0.5, 0)
    return combined

def send_pushover_notification(message, user_key, api_token):
    url = "https://api.pushover.net/1/messages.json"
    data = {
        "user": user_key,
        "token": api_token,
        "message": message
    }
    response = requests.post(url, data=data)
    return response.status_code

def calculate_winner(cpu_choice, player_choice):
    cpu_images = {
        "Rock": "1.png",
        "Paper": "2.png",
        "Scissors": "3.png"
    }

    cpu_image = cpu_images[cpu_choice]

    if player_choice == "Invalid":
        return "Invalid!", cpu_image

    if player_choice == cpu_choice:
        result = "Draw!"
    elif (player_choice == "Rock" and cpu_choice == "Scissors") or \
         (player_choice == "Paper" and cpu_choice == "Rock") or \
         (player_choice == "Scissors" and cpu_choice == "Paper"):
        result = "You Win!"
    else:
        result = "You Lose!"

    # Send Pushover notification
    user_key = "u2x4de3487tgkxndje7gvkeuerrgsw"
    api_token = "ach3x1ttic1uked8v67u4cte1zg8fc"
    message = f"Game result: {result}"
    send_pushover_notification(message, user_key, api_token)

    return result, cpu_image

def compute_fingers(hand_landmarks, count):
    if hand_landmarks[8][2] < hand_landmarks[6][2]:
        count += 1
    if hand_landmarks[12][2] < hand_landmarks[10][2]:
        count += 1
    if hand_landmarks[16][2] < hand_landmarks[14][2]:
        count += 1
    if hand_landmarks[20][2] < hand_landmarks[18][2]:
        count += 1
    if hand_landmarks[4][3] == "Left" and hand_landmarks[4][1] > hand_landmarks[3][1]:
        count += 1
    elif hand_landmarks[4][3] == "Right" and hand_landmarks[4][1] < hand_landmarks[3][1]:
        count += 1
    return count

webcam = cv2.VideoCapture(0)

success, image = webcam.read()
if not success:
    print("Camera isn't working")
    webcam.release()
    cv2.destroyAllWindows()
    exit()

mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_hands = mp.solutions.hands

cpu_choices = ["Rock", "Paper", "Scissors"]
cpu_choice = "Nothing"
cpu_score, player_score = 0, 0
winner_colour = (0, 255, 0)
player_choice = "Nothing"
hand_valid = False
display_values = ["Rock", "Invalid", "Scissors", "Invalid", "Invalid", "Paper"]
winner = "None"
de = deque(['Nothing'] * 5, maxlen=5)

def render_ui(image, player_choice, cpu_choice, winner, player_score, cpu_score, winner_colour):
    # Σκορ CPU και παίκτη
    cv2.putText(image, f"           {cpu_score}", (150, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
    cv2.putText(image, f"       {player_score}", (950, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
    
    # Επιλογές CPU και παίκτη
    cv2.putText(image, f"Player: {player_choice}", (850, 580), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
    cv2.putText(image, f"CPU: {cpu_choice}", (150, 580), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
    
    # Υπολογισμός θέσης για το μήνυμα νίκης/ήττας
    text_size = cv2.getTextSize(winner, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]  # Μικρότερη γραμματοσειρά
    text_x = (image.shape[1] - text_size[0]) // 2
    text_y = (image.shape[0] + text_size[1]) // 2 + 30  # Ελαφρώς πιο κάτω

    # Μήνυμα στο κέντρο
    cv2.putText(image, winner, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, winner_colour, 2)
    return image

background_path = './BG.png'
bot_images = ['./1.png', './2.png', './3.png']

with mp_hands.Hands(
        model_complexity=0,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5) as hands:

    background = cv2.imread(background_path)
    if background is None:
        print("Error loading background image!")
        exit()

    player_box = (850, 200, 350, 350)
    ai_box = (100, 230, 300, 300)

    cpu_image = None

    while webcam.isOpened():
        success, frame = webcam.read()
        if not success:
            print("Camera isn't working")
            break

        frame = cv2.flip(frame, 1)
        frame.flags.writeable = False
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame)
        frame.flags.writeable = True
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        handNumber = 0
        hand_landmarks = []
        isCounting = False
        count = 0

        if results.multi_hand_landmarks:
            isCounting = True

            if player_choice != "Nothing" and not hand_valid:
                hand_valid = True
                cpu_choice = random.choice(cpu_choices)
                winner, cpu_image_path = calculate_winner(cpu_choice, player_choice)

                cpu_image = cv2.imread(cpu_image_path, cv2.IMREAD_UNCHANGED)
                if cpu_image is None:
                    print("Error loading CPU image!")
                    continue

                if winner == "You Win!":
                    player_score += 1
                    winner_colour = (0, 255, 0)
                elif winner == "You Lose!":
                    cpu_score += 1
                    winner_colour = (0, 0, 255)
                elif winner == "Draw!":
                    winner_colour = (255, 255, 0)
                elif winner == "Invalid!":
                    winner_colour = (0, 255, 255)

            for hand in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    frame,
                    hand,
                    mp_hands.HAND_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(255, 0, 255), thickness=2, circle_radius=4),
                    mp_drawing.DrawingSpec(color=(0, 255, 255), thickness=2)
                )
                label = results.multi_handedness[handNumber].classification[0].label
                for id, landmark in enumerate(hand.landmark):
                    imgH, imgW, imgC = frame.shape
                    xPos, yPos = int(landmark.x * imgW), int(landmark.y * imgH)
                    hand_landmarks.append([id, xPos, yPos, label])
                count = compute_fingers(hand_landmarks, count)
                handNumber += 1
        else:
            player_choice = "Nothing"
            cpu_choice = "Nothing"
            winner = "None"
            hand_valid = False
            cpu_image = None

        if isCounting and count <= 5:
            player_choice = display_values[count]
        elif isCounting:
            player_choice = "Invalid"
        else:
            player_choice = "Nothing"

        de.appendleft(player_choice)
        try:
            player_choice = st.mode(de)
        except st.StatisticsError:
            print("Stats Error")
            continue

        display = background.copy()
        player_box = (796, 235, 398, 420)
        display = place_in_frame(display, frame, *player_box)

        ai_box = (130, 250, 300, 300)
        if cpu_image is not None:
            display = place_in_frame(display, cpu_image, *ai_box)

        display = render_ui(display, player_choice, cpu_choice, winner, player_score, cpu_score, winner_colour)

        cv2.imshow('Rock Paper Scissors', display)

        if cv2.waitKey(1) & 0xFF == 27:
            break

webcam.release()
cv2.destroyAllWindows()