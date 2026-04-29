# StockNexus AI 🏪

**Smart Kirana Command Center** - An AI-powered inventory management system tailored for Indian retail, featuring live stock tracking, credit books (Khata), expense management, and predictive analytics.

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![AI](https://img.shields.io/badge/AI-LLAMA%203.3-8A2BE2?style=for-the-badge&logo=meta&logoColor=white)](https://groq.com/)

---

## 🌟 Key Features

- 📊 **Real-time Inventory Tracking**: Automated stock level monitoring with low-stock alerts.
- 💳 **Smart Khata (Credit Book)**: Digital ledger for customer debts and payments with loyalty point tracking.
- 📉 **Predictive Analytics**: LSTM-powered demand forecasting to optimize restocking schedules.
- 🤖 **AI Assistant**: Groq-powered chat interface for business insights and automated promo generation.
- 🧾 **Invoice Scanner**: OCR-based inventory updates from supplier invoices.
- 💰 **Expense Tracking**: Simplified daily business expense logging.
- 🔄 **Dual Mode**: Seamlessly switch between Cloud (Supabase) and Local (CSV) storage.

---

## 📸 Screenshots

### 🔑 Secure Authentication
![Login Page](screenshots/login.png)

### 📊 Kirana Command Center (Dashboard)
![Dashboard](screenshots/dashboard.png)

### 📦 Inventory Management
![Inventory](screenshots/inventory.png)

### 🔮 AI Predictions
![Predictions](screenshots/predict.png)

---

## 🛠️ Tech Stack

- **Frontend**: HTML5, Vanilla CSS3 (Glassmorphism), JavaScript (ES6+)
- **Backend**: Python 3, Flask
- **Database**: PostgreSQL (Supabase) with Connection Pooling
- **AI/ML**: TensorFlow (LSTM), Groq (LLaMA 3.3), Scikit-learn
- **Data**: Pandas, Numpy

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/Yashwant-king/StockNexusAI.git
cd StockNexusAI
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
Create a `.env` file from the template:
```bash
cp .env.example .env
# Edit .env with your actual keys
```

### 4. Run the Application
```bash
python run.py
```
Access the dashboard at `http://localhost:5000`

---

## 🏗️ Architecture

StockNexus AI follows a modular monolithic architecture, utilizing:
- **Global Auth Hook**: Centralized session management.
- **CSV Fallback**: Automatic fallback to local storage if DB connection fails.
- **Predictive Engine**: Integrated training pipeline for custom shop data.

---

## 📝 License
This project is for demonstration and kirana store optimization purposes. Built with ❤️ by StockNexus AI.
