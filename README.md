## Northstar Task Operations

Activate the virtual environment and install dependencies:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Start the API locally:

```powershell
python app.py
```

Test the endpoints:

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/health
Invoke-RestMethod http://127.0.0.1:5000/api/tasks
Invoke-RestMethod http://127.0.0.1:5000/api/stats
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5000/api/tasks -ContentType 'application/json' -Body '{"title":"Ship the next improvement","priority":"high"}'
```

Available endpoints:

- `GET /api/health`
- `GET /api/tasks?q=&status=&priority=`
- `GET /api/stats`
- `POST /api/tasks` with `title`, `description`, `priority`, and `due_date`
- `PATCH /api/tasks/:id` to update a task
- `DELETE /api/tasks/:id`

The dashboard is served at `http://127.0.0.1:5000/`. Data is stored in `tasks.db` using SQLite.
