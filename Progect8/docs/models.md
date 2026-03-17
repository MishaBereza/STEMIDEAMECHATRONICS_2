# models.py

## Опис моделей

### User
- id: int PK
- first_name, last_name: String(120), non-null
- email: String(200), unique, non-null
- age: int nullable
- bio: Text nullable
- role: String(30, default='team')
- property `name`: full name

### Tournament
- id: int PK
- name: String(200), non-null
- description: Text
- max_teams: int
- status: String(30, default='Draft')
- `rounds`: як список `Round` через backref

### team_members
- association table team_id + user_id (many-to-many)

### Team
- id: int PK
- name: String(200), non-null
- captain_id: FK->User.id
- captain: relationship User
- members: many-to-many with User (excluding captain) через team_members, lazy='dynamic'
- tournament_id: FK->Tournament
- submissions: relationship Submission backref team
- repo_url, live_url, comments, submitted_at, submission_status

### Round
- id: int PK
- tournament_id: FK->Tournament
- title: String(200), non-null
- description: Text
- must_have: Text
- start_at/end_at: DateTime
- level: int default 1
- status: String(30, default='Draft')
- submissions: relationship Submission

### Submission
- id: int PK
- team_id: FK->Team
- round_id: FK->Round
- repo_url, demo_url, description, submitted_at (utc now)
- evaluations: relationship Evaluation

### Evaluation
- id: int PK
- submission_id: FK->Submission
- jury_id: FK->User
- score_tech, score_func, score_ui float
- comment: Text
- total(): сума наявних score_* (ігнор None)
