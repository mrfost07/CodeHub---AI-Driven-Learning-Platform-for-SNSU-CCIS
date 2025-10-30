# CodeHub - Quick Start Guide

## 🚀 Quick Start (Development)

### Step 1: Backend Setup

```bash
# Navigate to backend directory
cd codehub_backend

# Activate virtual environment
# Windows:
..\venv\Scripts\activate
# Linux/Mac:
source ../venv/bin/activate

# Install dependencies (already done)
pip install -r requirements.txt

# Run migrations (already done)
python manage.py migrate

# Create superuser (if not created)
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

Backend will be available at: **http://localhost:8000**

### Step 2: Frontend Setup

```bash
# Open a new terminal
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

Frontend will be available at: **http://localhost:3000**

### Step 3: Access the Application

1. **Frontend Dashboard**: http://localhost:3000
2. **Backend API**: http://localhost:8000/api
3. **Admin Panel**: http://localhost:8000/admin

## 📋 Default Credentials

Create your own using:
```bash
python manage.py createsuperuser
```

## 🔧 Environment Variables

### Backend (.env in codehub_backend/)
```env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///db.sqlite3
OPENAI_API_KEY=your-openai-key  # Optional for AI features
```

### Frontend (.env in frontend/)
```env
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_WS_URL=ws://localhost:8000/ws
```

## 🐳 Docker Setup (Alternative)

```bash
# Start all services
docker-compose up -d

# Run migrations
docker-compose exec backend python manage.py migrate

# Create superuser
docker-compose exec backend python manage.py createsuperuser

# View logs
docker-compose logs -f
```

## 📚 API Documentation

Once the backend is running, visit:
- Browsable API: http://localhost:8000/api/
- Admin Panel: http://localhost:8000/admin/

## 🎯 Key Features to Test

### 1. Authentication
- Register: http://localhost:3000/register
- Login: http://localhost:3000/login

### 2. Learning System
- View Career Paths
- Access Learning Modules
- Take Quizzes
- Track Progress

### 3. Project Collaboration
- Create Projects
- Manage Tasks (Kanban board)
- Real-time Code Editing
- Code Reviews

### 4. Community
- Create Posts
- Comment and Like
- Real-time Notifications
- Follow Users

### 5. AI Mentor
- Chat with AI
- Code Analysis
- Get Learning Recommendations
- Project Guidance

## 🔍 Available API Endpoints

### Authentication
- `POST /api/auth/register/` - Register new user
- `POST /api/auth/login/` - Login
- `GET /api/auth/profile/` - Get user profile
- `PUT /api/auth/profile/` - Update profile

### Learning
- `GET /api/learning/career-paths/` - List career paths
- `GET /api/learning/modules/` - List modules
- `GET /api/learning/progress/` - User progress
- `POST /api/learning/quizzes/{id}/start/` - Start quiz

### Projects
- `GET /api/projects/` - List projects
- `POST /api/projects/` - Create project
- `GET /api/projects/{id}/tasks/` - Project tasks
- `GET /api/projects/{id}/files/` - Project files

### Community
- `GET /api/community/posts/` - List posts
- `POST /api/community/posts/` - Create post
- `GET /api/community/feed/` - Personalized feed
- `GET /api/community/notifications/` - Notifications

### AI Mentor
- `POST /api/ai-mentor/send-message/` - Send message
- `POST /api/ai-mentor/analyze-code/` - Analyze code
- `GET /api/ai-mentor/recommendations/` - Get recommendations

## 🛠️ Troubleshooting

### Backend issues
```bash
# Reset database
python manage.py flush
python manage.py migrate

# Collect static files
python manage.py collectstatic

# Check for errors
python manage.py check
```

### Frontend issues
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear browser cache
# Press Ctrl+Shift+Delete in browser
```

### WebSocket connection issues
1. Ensure Redis is running (for production)
2. Check CORS settings in backend
3. Verify WebSocket URL in frontend .env

## 📞 Need Help?

- Check the full README.md for detailed information
- Review the API documentation at http://localhost:8000/api/
- Check the browser console for frontend errors
- Check backend logs for server errors

## 🎉 You're All Set!

The CodeHub platform is now running and ready for development or testing. Happy coding!

