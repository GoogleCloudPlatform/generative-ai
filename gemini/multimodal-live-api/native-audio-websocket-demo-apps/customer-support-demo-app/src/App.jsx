import { useState, useRef } from "react";
import LiveAPIDemo from "./components/LiveAPIDemo";
import "./App.css";

function App() {
  const liveApiRef = useRef(null);

  return (
    <div className="App">
      <LiveAPIDemo ref={liveApiRef} />
    </div>
  );
}

export default App;
