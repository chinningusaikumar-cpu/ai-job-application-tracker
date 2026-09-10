import React from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

function App() {
  return (
    <main className="app">
      <h1>AI Job Application Tracker</h1>
      <p>Your intelligent career dashboard starts here.</p>
      <section className="cards">
        <div><strong>0</strong><span>Applications</span></div>
        <div><strong>0</strong><span>Interviews</span></div>
        <div><strong>0</strong><span>Offers</span></div>
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
