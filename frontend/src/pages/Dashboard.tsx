import React from "react";

const DashboardPage: React.FC = () => {
  return (
    <div className="w-full max-w-2xl bg-white/80 rounded-2xl shadow-2xl p-10 flex flex-col items-center">
      <h1 className="text-3xl font-extrabold text-[#2c3e42] tracking-widest mb-2">Dashboard</h1>
      <p className="text-[#3a5a60] mb-6">Gerencie seus clientes e agendamentos com facilidade.</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
        <div className="bg-yellow-100/80 rounded-xl p-6 shadow flex flex-col items-center">
          <span className="text-5xl font-bold text-[#3a5a60]">24</span>
          <span className="text-[#2c3e42] mt-2 font-semibold">Clientes</span>
        </div>
        <div className="bg-yellow-100/80 rounded-xl p-6 shadow flex flex-col items-center">
          <span className="text-5xl font-bold text-[#3a5a60]">12</span>
          <span className="text-[#2c3e42] mt-2 font-semibold">Agendamentos</span>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;