import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { Spinner } from "@/components/ui/Spinner";
import Layout from "@/components/Layout";
import Login from "@/pages/Login";
import Upload from "@/pages/Upload";
import Historico from "@/pages/Historico";
import Resultado from "@/pages/Resultado";
import Admin from "@/pages/Admin";
import Apendice01 from "@/pages/Apendice01";
import Apendice02 from "@/pages/Apendice02";

function Guard({ children, admin }: { children: React.ReactNode; admin?: boolean }) {
  const { me, loading } = useAuth();
  if (loading) return <div className="min-h-screen flex items-center justify-center"><Spinner className="w-8 h-8" /></div>;
  if (!me) return <Navigate to="/login" replace />;
  if (admin && me.role !== "admin") return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Guard><Layout><Upload /></Layout></Guard>} />
      <Route path="/historico" element={<Guard><Layout><Historico /></Layout></Guard>} />
      <Route path="/resultado/:id" element={<Guard><Layout><Resultado /></Layout></Guard>} />
      <Route path="/apendice01" element={<Guard><Layout><Apendice01 /></Layout></Guard>} />
      <Route path="/apendice02" element={<Guard><Layout><Apendice02 /></Layout></Guard>} />
      <Route path="/admin" element={<Guard admin><Layout><Admin /></Layout></Guard>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
