# 🏪 StockNexus AI — Kirana Command Center

An advanced AI-powered inventory, khata (credit), and business management system specifically built for Indian Kirana stores. Built with Flask, Supabase (PostgreSQL), and Groq AI.

## ✨ Features

- **📦 Smart Inventory Management**: Track stock levels, set minimum stock alerts, and monitor expiry dates.
- **📒 Digital Khata (Credit Book)**: Replace your physical ledger. Track customers, udhar (credit), and payments seamlessly.
- **💸 Expense Tracking**: Keep an eye on shop expenses (electricity, rent, supplies) to calculate true net profit.
- **🤖 LLaMA-Powered AI Assistant**: Chat with your store data! The AI knows your stock, khata balances, and expenses. Ask "Which items are expiring soon?" or "Who owes me the most money?"
- **📱 WhatsApp Integration**: Send automated payment reminders, promotional messages, and daily business reports directly to WhatsApp.
- **📈 AI Sales Predictions**: Predict next month's sales based on historical data using an integrated AI model.
- **📊 Analytics Dashboard**: Visualize revenue, top-selling products, and stock health at a glance.

## 🛠️ Tech Stack

- **Backend**: Python, Flask
- **Frontend**: HTML5, Vanilla JavaScript, CSS (Glassmorphism UI)
- **Database**: Supabase (PostgreSQL) + local CSV fallback
- **AI / LLM**: Groq API (LLaMA 3.3 70B Versatile)
- **Deployment**: Render

## 🚀 Live Demo
Access the live application here: [StockNexus AI on Render](https://stocknexusai-2.onrender.com)

## 💻 Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Yashwant-king/StockNexusAI.git
   cd StockNexusAI
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Variables:**
   Create a `.env` file in the root directory and add the following keys:
   ```env
   SECRET_KEY=your_secret_key_here
   GROQ_API_KEY=your_groq_api_key
   DATABASE_URL=postgresql://postgres.your_supabase_url
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```
   The app will run at `http://127.0.0.1:5000`

## 🔒 Security Note
This project requires user authentication. Ensure `SECRET_KEY` is set in production.

## 🤝 Contributing
Contributions, issues, and feature requests are welcome!

## 📝 License
This project is open source and available under the [MIT License](LICENSE).
