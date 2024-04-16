import AgentAssist from "./pages/AgentAssist";
import HomePage from "./pages/HomePage";
import Layout from "./pages/Layout";
import WorkBenchPage from "./pages/WorkbenchPage";
import { Routes, Route, MemoryRouter } from "react-router-dom";

function App() {
  return (
    <MemoryRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="workbench" element={<WorkBenchPage />} />
          <Route path="agent_assist" element={<AgentAssist />} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

export default App;
