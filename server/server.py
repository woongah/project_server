from flask import Flask, request, jsonify, render_template
import sqlite3
import json
import threading
from collections import Counter
import json


app = Flask(__name__)

DATABASE = 'game_data.db'
conn = sqlite3.connect(DATABASE, check_same_thread=False)
cursor = conn.cursor()

conn.execute('''CREATE TABLE IF NOT EXISTS player (
                        name TEXT NOT NULL PRIMARY KEY,
                        wins INTEGER NOT NULL DEFAULT 0,
                        losses INTEGER NOT NULL DEFAULT 0,
                        score INTEGER NOT NULL DEFAULT 0
                    );''')
conn.execute('''CREATE TABLE IF NOT EXISTS game ( 
                        id INTEGER PRIMARY KEY AUTOINCREMENT,      
                        player_name TEXT NOT NULL,
                        is_win BOOLEAN NOT NULL,
                        stat_points TEXT NOT NULL,
                        chosen_skills INTEGER NOT NULL CHECK (chosen_skills IN (0, 1, 2)),
                        FOREIGN KEY(player_name) REFERENCES player(name)
                    );''')
conn.commit()

# client 전송 파일 예시
# [
#     {
#         "player_name": "Player1",
#         "is_win": true,
#         "stat_points": [8, 6, 6],
#         "chosen_skills": [1, 2]
#     },
#     {
#         "player_name": "Player2",
#         "is_win": false,
#         "stat_points": [5, 7, 8],
#         "chosen_skills": [3, 4]
#     }
# ]

@app.route('/submit_game', methods=['POST'])
def submit_game():
    data = request.json

    for player_data in data:
        player_name = player_data['player_name']
        is_win = player_data['is_win']
        score_change = 2 if is_win else -1
        win = 0
        loss = 0
        if is_win : win = 1 
        else : loss = 1 
        

        # Player 점수, 전적 업데이트
        conn.execute('INSERT OR IGNORE INTO player (name, score, wins, losses) VALUES (?, 0, 0, 0)', (player_name,))
        conn.execute('UPDATE player SET score = score + ? WHERE name = ?', (score_change, player_name))
        conn.execute('UPDATE player SET wins = wins + ? WHERE name = ?', (win, player_name))
        conn.execute('UPDATE player SET losses = losses + ? WHERE name = ?', (loss, player_name))

        # Game 데이터 추가
        stat_points = ','.join(map(str, player_data['stat_points']))
        chosen_skills = ','.join(map(str,player_data['chosen_skills']))
        conn.execute('INSERT INTO game (player_name, is_win, stat_points, chosen_skills) VALUES (?, ?, ?, ?)',
                     (player_name, is_win, stat_points, chosen_skills))
    
    conn.commit()
    return jsonify({"message": "Game data submitted successfully."})

@app.route('/player_stats', methods=['GET'])
def player_stats():
    players = conn.execute('SELECT * FROM player ORDER BY score DESC LIMIT 5').fetchall()
    player_data = []

    for player in players:
        recent_games = conn.execute('SELECT * FROM game WHERE player_name = ? ORDER BY id DESC LIMIT 5', (player[0],)).fetchall()
        avg_stats = calculate_average_stats(recent_games)
        common_skills = list(map(int, get_common_skills(recent_games)))
        player_data.append({
            'name': player[0],            
            'score': player[3],
            'wins': player[1],
            'losses': player[2],
            'average_stats': avg_stats,
            'common_skills': common_skills

        })

    return jsonify(player_data)

def calculate_average_stats(games):
    if not games:  # 게임 기록이 없을 경우
        return [0, 0, 0]  # 평균을 0으로 설정

    total_stats = [0, 0, 0]
    for game in games:
        stats = list(map(int, game[3].split(',')))
        total_stats = [total + stat for total, stat in zip(total_stats, stats)]
    
    avg_stats = [total / len(games) if len(games) > 0 else 0 for total in total_stats]  # 여기서 ZeroDivisionError를 방지
    return avg_stats


def get_common_skills(games):
    skill_counts = Counter()
    for game in games:
        skills = game[4].split(',')
        skill_counts.update(skills)
    most_common = skill_counts.most_common(2)
    return [skill[0] for skill in most_common]


@app.route('/')
def index():
    return render_template('index.html', content='')

@app.route('/player_info', methods=['POST'])
def player_info():
    player_name = request.form['player_name']

    # 플레이어 정보 조회
    cursor.execute("SELECT * FROM player WHERE name = ?", (player_name,))
    player_result = cursor.fetchone()

    if player_result:
        player_info_html = f'''
        <h1>{player_result[0]}</h1>
        <p>승리 수: {player_result[1]}</p>
        <p>패배 수: {player_result[2]}</p>
        <p>스코어: {player_result[3]}</p>
        '''

        # 플레이어의 게임 정보 조회
        cursor.execute("SELECT * FROM game WHERE player_name = ? LIMIT 5", (player_name,))
        games = cursor.fetchall()

        if games:
            games_html = "<h2>최근 게임 정보:</h2>"
            games_html += "<ul>"
            for game in games:
                games_html += f"<li>게임 ID: {game[0]}, 승리 여부: {'승리' if game[2] else '패배'}, 스탯 포인트: {game[3]}, 선택한 스킬: {game[4]}</li>"
            games_html += "</ul>"
        else:
            games_html = "<p>게임 기록이 없습니다.</p>"

        return render_template('index.html', content=player_info_html + games_html)
    else:
        return render_template('index.html', content="플레이어를 찾을 수 없습니다.")


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)  
