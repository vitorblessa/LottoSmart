import { BrowserRouter, Routes, Route, NavLink, useLocation } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { useState, useEffect } from "react";
import Dashboard from "./pages/Dashboard";
import QuinaPage from "./pages/QuinaPage";
import DuplaSenaPage from "./pages/DuplaSenaPage";
import HistoryPage from "./pages/HistoryPage";
import StatisticsPage from "./pages/StatisticsPage";
import { Home, Sparkles, Cherry, History, BarChart3, Menu, X } from "lucide-react";
import "@/App.css";

const NavItem = ({ to, icon: Icon, label, variant }) => {
  const location = useLocation();
  const isActive = location.pathname === to;
  
  const baseClasses = "flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-300 font-medium";
  const variantClasses = {
    quina: isActive 
      ? "bg-violet-600/20 text-violet-400 border border-violet-500/30" 
      : "text-slate-400 hover:text-violet-400 hover:bg-violet-600/10",
    dupla: isActive 
      ? "bg-rose-600/20 text-rose-400 border border-rose-500/30" 
      : "text-slate-400 hover:text-rose-400 hover:bg-rose-600/10",
    default: isActive 
      ? "bg-white/10 text-white border border-white/20" 
      : "text-slate-400 hover:text-white hover:bg-white/5"
  };
  
  return (
    <NavLink to={to} className={`${baseClasses} ${variantClasses[variant || "default"]}`} data-testid={`nav-${to.replace("/", "") || "home"}`}>
      <Icon size={20} />
      <span className="hidden md:inline">{label}</span>
    </NavLink>
  );
};

const Sidebar = ({ isOpen, onClose }) => {
  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 md:hidden" 
          onClick={onClose}
        />
      )}
      
      {/* Sidebar */}
      <aside className={`
        fixed md:sticky top-0 left-0 h-screen w-64 md:w-20 lg:w-64 
        bg-zinc-950/80 backdrop-blur-xl border-r border-white/5
        z-50 transform transition-transform duration-300 ease-in-out
        ${isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
      `}>
        <div className="flex flex-col h-full p-4">
          {/* Logo */}
          <div className="flex items-center justify-between mb-8 px-2">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-600 to-rose-600 flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <span className="font-heading font-bold text-xl text-white hidden lg:block">LottoSmart</span>
            </div>
            <button onClick={onClose} className="md:hidden text-slate-400 hover:text-white">
              <X size={24} />
            </button>
          </div>
          
          {/* Navigation */}
          <nav className="flex flex-col gap-2">
            <NavItem to="/" icon={Home} label="Dashboard" />
            <NavItem to="/quina" icon={Sparkles} label="Quina" variant="quina" />
            <NavItem to="/dupla-sena" icon={Cherry} label="Dupla Sena" variant="dupla" />
            <NavItem to="/historico" icon={History} label="Histórico" />
            <NavItem to="/estatisticas" icon={BarChart3} label="Estatísticas" />
          </nav>
          
          {/* Footer */}
          <div className="mt-auto pt-4 border-t border-white/5">
            <p className="text-xs text-slate-500 text-center hidden lg:block">
              Apostas inteligentes baseadas em análise estatística
            </p>
          </div>
        </div>
      </aside>
    </>
  );
};

const Layout = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  
  return (
    <div className="flex min-h-screen bg-[#020204]">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      
      <main className="flex-1 min-h-screen">
        {/* Mobile Header */}
        <header className="md:hidden sticky top-0 z-30 bg-zinc-950/80 backdrop-blur-xl border-b border-white/5 px-4 py-3">
          <div className="flex items-center justify-between">
            <button 
              onClick={() => setSidebarOpen(true)} 
              className="text-slate-400 hover:text-white"
              data-testid="mobile-menu-btn"
            >
              <Menu size={24} />
            </button>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-600 to-rose-600 flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <span className="font-heading font-bold text-lg text-white">LottoSmart</span>
            </div>
            <div className="w-6" /> {/* Spacer */}
          </div>
        </header>
        
        {/* Page Content */}
        <div className="p-4 md:p-6 lg:p-8">
          {children}
        </div>
      </main>
      
      {/* Noise Overlay */}
      <div className="noise-overlay" />
      
      {/* Toast Notifications */}
      <Toaster 
        position="top-right" 
        toastOptions={{
          style: {
            background: "#18181b",
            border: "1px solid rgba(255,255,255,0.1)",
            color: "#fff"
          }
        }}
      />
    </div>
  );
};

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/quina" element={<QuinaPage />} />
          <Route path="/dupla-sena" element={<DuplaSenaPage />} />
          <Route path="/historico" element={<HistoryPage />} />
          <Route path="/estatisticas" element={<StatisticsPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
