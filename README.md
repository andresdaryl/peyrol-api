## 📘 **Peyrol Backend**

### 🧾 Overview

**Peyrol** is a backend API built with **FastAPI**, **PostgreSQL**, and **SQLAlchemy** for managing payrolls, employees, and payslip generation.
It's designed to integrate seamlessly with your frontend (React or any REST client).


---

### 🔧 **Setup & Installation**

#### 1️⃣ Clone the repository

```bash
git clone https://github.com/andresdaryl/peyrol-api.git
cd peyrol-api
```

#### 2️⃣ Create and activate virtual environment

```bash
python -m venv venv
source venv/bin/activate      # Mac/Linux
venv\Scripts\activate         # Windows
```

#### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```


---

### ⚙️ **Environment Variables**

All configuration values are stored in a `.env` file.
A sample file is provided as `.env.example` — you can copy it to create your own local config.

```bash
cp .env.example .env
```

Then edit `.env` with your actual credentials.


---

### 🧱 **Database Setup**

#### Initialize Alembic (first time)

```bash
alembic init alembic
```

#### Generate migration

```bash
alembic revision --autogenerate -m "Initial migration"
```

#### Apply migration

```bash
alembic upgrade head
```


---

### 🚀 **Run the Server**

#### Development

```bash
uvicorn app.main:app --reload
```

Visit:
👉 [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)
👉 [http://localhost:8000/redoc](http://localhost:8000/redoc) (ReDoc)


---

### 👤 **Author**

**Daryl Andres**
🛠️ Full Stack Developer
🌐 [https://github.com/andresdaryl](https://github.com/andresdaryl)