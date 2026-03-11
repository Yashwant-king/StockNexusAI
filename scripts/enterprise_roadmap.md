## StockNexus AI: Enterprise Roadmap

### 1. AI Assistant (LLM Retail Assistant)
We need to integrate an LLM (like Google Gemini or Langchain) directly into the dashboard so users can "Chat with their database" to get instant answers about stock levels, pricing, and advice.

### 2. CRM (Customer Tracking + Chatbot)
The system currently tracks products, not people. We need to add a Customer Database (CRM) and attach purchase history to specific users to enable targeted marketing.

### 3. Supply Chain (Predictive Inventory)
*(Partially Completed)* We have an LSTM predicting future sales volume. We need to expand this to "Predictive Ordering," where it automatically generates Vendor Purchase Orders when stock gets low.

### 4. Market Insights (Clustering & Segmentation)
We will implement an Unsupervised Machine Learning algorithm (like K-Means Clustering) to group products automatically into categories (e.g., "High-Profit Slow-Movers", "Low-Profit Fast-Movers") without the user defining them.

### 5. Fraud Detection (Anomaly Detection)
We will add an Isolation Forest algorithm that scans the inventory updates and flags suspicious activities (e.g., if a high-value item's stock drops by 5 units without a recorded sale, it triggers an "Anomaly Alert").

### 6. Accessibility (Vernacular UI)
We will add an AI translation layer to the frontend so the dashboard can instantly switch to Hindi, Spanish, or Mandarin for warehouse workers, converting product names and AI insights dynamically.
