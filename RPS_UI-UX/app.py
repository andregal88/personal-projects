from flask import Flask, request, jsonify
import json

app = Flask(__name__)

@app.route('/')
def home():
    return "Welcome to the Rock Paper Scissors Game!"

# Add other routes as needed

@app.route('/play', methods=['POST'])
def play_game():
    data = request.json
    player_choice = data['player_choice']

    # Assuming calculate_winner function is adapted to take just player_choice
    # and returns both the winner and cpu_choice
    winner, cpu_choice = calculate_winner(player_choice)

    response = {
        "player_choice": player_choice,
        "cpu_choice": cpu_choice,
        "winner": winner
    }

    return jsonify(response)


player_score = 0
cpu_score = 0

@app.route('/score', methods=['GET', 'POST'])
def score():
    global player_score, cpu_score
    if request.method == 'POST':
        winner = request.json['winner']
        if winner == 'You Win!':
            player_score += 1
        elif winner == 'You Lose!':
            cpu_score += 1
    return jsonify({"player_score": player_score, "cpu_score": cpu_score})

if __name__ == '__main__':
    app.run(debug=True)
