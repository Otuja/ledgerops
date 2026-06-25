# CROO Agent Protocol - Frontend Dashboard

This is the React frontend dashboard for the Automated Transaction Logging Agent.

## Tech Stack
- **React 19**
- **Vite** (Build Tool)
- **Tailwind CSS** (Styling)

## Features
- Premium Dark-mode Developer Portal UI.
- Tabular layout for displaying immutable `TransactionAuditLog` records.
- Aggregate counter for managed virtual wallet `balance_usdc`.

## Running Locally

To install dependencies and start the development server:
```bash
npm install
npm run dev
```

The application will start on `http://localhost:5173`. 

## Integration & Deployment
The UI is built to fetch from your Django backend. 

**Local Development:**
By default, it will fetch from `http://localhost:8000/api`. If the API is unreachable, it defaults to a beautiful mock data state so you can preview and demo the application instantly.

**Production Deployment:**
When you deploy this frontend (e.g., to Vercel, Netlify, or Render), you need to tell it where your live backend is hosted. 
You can do this by setting an environment variable named `VITE_API_URL` in your deployment platform's dashboard:
```env
VITE_API_URL=https://your-production-django-domain.com/api
```
Alternatively, you can create a `.env` file in the root of this `croo_dashboard` folder for testing production URLs locally.
