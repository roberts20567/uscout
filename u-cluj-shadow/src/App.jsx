import React, { useState } from 'react';
import { mockProjects as initialProjects, currentSquad, scoutedPool } from './mockData';
import TacticalPitch from './TacticalPitch';

// Utility for performance indicators (Green for growth, Red for risk)
const DeltaTag = ({ value }) => (
  <span className={`text-[10px] font-black px-1 ${value >= 0 ? 'bg-green-500 text-white' : 'bg-red-600 text-white'}`}>
    {value >= 0 ? '+' : ''}{value}%
  </span>
);

export default function App() {
  // --- CORE STATE ---
  const [view, setView] = useState('home'); 
  const [projects, setProjects] = useState(initialProjects);
  const [activeProject, setActiveProject] = useState(null);
  const [selectedProspect, setSelectedProspect] = useState(null);
  const [heatmap, setHeatmap] = useState(false);

  // --- MODAL / SCOUTING STATE ---
  const [targetPlayer, setTargetPlayer] = useState(null);
  const [selectedPoolIds, setSelectedPoolIds] = useState([]);

  // --- HANDLERS ---
  const handleCreateProject = () => {
    const selectedProspects = scoutedPool.filter(p => selectedPoolIds.includes(p.id));
    const newProj = {
      id: Date.now(),
      title: `${targetPlayer.position} UPGRADE: ${targetPlayer.name.split(' ').pop()}`,
      description: `Targeting replacements for ${targetPlayer.name}`,
      prospects: selectedProspects
    };
    setProjects([newProj, ...projects]);
    setTargetPlayer(null);
    setSelectedPoolIds([]);
  };

  const handleDeleteProject = (e, id) => {
    e.stopPropagation(); // Stops the project from opening when clicking delete
    if (window.confirm("Confirm: Delete this scouting project?")) {
      const updated = projects.filter(p => p.id !== id);
      setProjects(updated);
      if (activeProject?.id === id) setView('home');
    }
  };

  return (
    <div className="flex h-screen bg-white font-sans text-black overflow-hidden relative">
      
      {/* --- 1. SCOUTING MODAL (MULTI-SELECT) --- */}
      {targetPlayer && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-md p-4">
          <div className="bg-white border-4 border-black shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] w-full max-w-md p-6 flex flex-col max-h-[85vh]">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h2 className="text-2xl font-black uppercase italic tracking-tighter">Scout: {targetPlayer.position}</h2>
                <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Select targets for simulation</p>
              </div>
              <button onClick={() => setTargetPlayer(null)} className="font-black text-xl hover:scale-125 transition-transform">✕</button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 pr-1">
              {scoutedPool
                .filter(p => p.position === targetPlayer.position)
                .sort((a, b) => (b.rating + b.synergy) - (a.rating + a.synergy))
                .map(p => {
                  const isChecked = selectedPoolIds.includes(p.id);
                  return (
                    <div 
                      key={p.id}
                      onClick={() => setSelectedPoolIds(prev => isChecked ? prev.filter(id => id !== p.id) : [...prev, p.id])}
                      className={`p-3 border-2 border-black cursor-pointer flex justify-between items-center transition-all ${isChecked ? 'bg-black text-white translate-x-1 translate-y-1 shadow-none' : 'bg-white shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:bg-gray-50'}`}
                    >
                      <div className="flex flex-col">
                        <span className="text-[11px] font-black uppercase tracking-tight">{p.name}</span>
                        <span className="text-[8px] opacity-60 font-bold uppercase tracking-widest">
                          Fit Score: {p.rating + p.synergy}
                        </span>
                      </div>
                      <div className={`w-5 h-5 border-2 border-current flex items-center justify-center font-black ${isChecked ? 'bg-green-500' : ''}`}>
                        {isChecked && '✓'}
                      </div>
                    </div>
                  );
                })}
            </div>

            <button 
              disabled={selectedPoolIds.length === 0} 
              onClick={handleCreateProject} 
              className="mt-6 w-full p-4 bg-black text-white font-black uppercase italic border-4 border-black hover:bg-white hover:text-black disabled:opacity-20 transition-all"
            >
              Start Project ({selectedPoolIds.length} Targets)
            </button>
          </div>
        </div>
      )}

      {/* --- 2. LEFT SIDEBAR (NAVIGATION & ACTIVE PROJECTS) --- */}
      <aside className="w-80 border-r-4 border-black p-6 bg-gray-50 flex flex-col">
        <h2 className="text-5xl font-black uppercase mb-8 italic tracking-tighter select-none">USCOUT</h2>
        
        {view === 'home' ? (
          <>
            <button 
              onClick={() => setHeatmap(!heatmap)} 
              className={`w-full mb-8 p-3 border-4 border-black font-black uppercase text-xs shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] active:translate-x-1 active:translate-y-1 active:shadow-none transition-all ${heatmap ? 'bg-red-600 text-white border-red-600' : 'bg-white'}`}
            >
              {heatmap ? 'Deactivate Heatmap' : 'Analyze Team Heatmap'}
            </button>
            <div className="mb-6 bg-yellow-300 border-2 border-black p-2 text-[9px] font-black uppercase animate-pulse text-center">
              Click player on field to scout
            </div>
            <p className="text-[10px] font-black uppercase text-gray-400 mb-4 tracking-widest border-b-2 border-gray-200 pb-2">Active Projects</p>
            
            <div className="space-y-6 overflow-y-auto pr-4 py-4">
              {projects.map(proj => (
                <div key={proj.id} className="relative">
                  <button 
                    onClick={() => { setActiveProject(proj); setView('project'); setSelectedProspect(proj.prospects[0]); }} 
                    className="w-full text-left p-4 border-[4px] border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:bg-black hover:text-white transition-all bg-white"
                  >
                    <h3 className="font-black uppercase text-sm leading-none">{proj.title}</h3>
                    <p className="text-[9px] uppercase mt-2 opacity-60 font-bold">{proj.prospects.length} Targets Selected</p>
                  </button>
                  {/* CLEAN PINNED DELETE BUTTON */}
                  <button 
                    onClick={(e) => handleDeleteProject(e, proj.id)} 
                    className="absolute -top-2 -right-2 z-30 w-7 h-7 bg-red-600 text-white border-[3px] border-black font-black text-[14px] flex items-center justify-center hover:bg-black hover:scale-110 transition-all"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="flex flex-col h-full">
            <button onClick={() => setView('home')} className="mb-8 font-black uppercase text-xs border-2 border-black p-2 hover:bg-black hover:text-white transition-all">← BACK TO OVERVIEW</button>
            <h2 className="text-xl font-black uppercase mb-6 italic border-b-4 border-black pb-2 leading-tight">{activeProject.title}</h2>
            <div className="space-y-3 overflow-y-auto pr-2">
              {activeProject.prospects.map(p => {
                const isSelected = selectedProspect?.id === p.id;
                const statusShadow = p.delta >= 0 ? 'shadow-[4px_4px_0px_0px_rgba(34,197,94,1)]' : 'shadow-[4px_4px_0px_0px_rgba(220,38,38,1)]';
                return (
                  <div 
                    key={p.id} 
                    onClick={() => setSelectedProspect(p)} 
                    className={`p-3 border-2 border-black cursor-pointer transition-all ${isSelected ? `bg-black text-white ${statusShadow} -translate-x-1 -translate-y-1` : 'bg-white hover:bg-gray-50'}`}
                  >
                    <div className="flex justify-between font-black text-[10px] uppercase italic">
                      <span>{p.name}</span>
                      <span className={p.delta >= 0 ? 'text-green-400' : 'text-red-500'}>
                        {p.delta >= 0 ? '+' : ''}{p.delta}%
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </aside>

      {/* --- 3. CENTER MAIN: THE SIMULATOR FIELD --- */}
      <main className="flex-1 p-10 flex flex-col items-center justify-center bg-[#fdfdfd]">
        <div className="w-full max-w-lg">
          <TacticalPitch 
            squad={currentSquad} 
            shadowPlayer={view === 'project' ? selectedProspect : null} 
            showHeatmap={heatmap} 
            onPlayerClick={(p) => view === 'home' && setTargetPlayer(p)} 
          />
        </div>
      </main>

      {/* --- 4. RIGHT SIDEBAR: IN-DEPTH DATA PANEL --- */}
      {view === 'project' && selectedProspect && (
        <aside className="w-96 border-l-4 border-black p-8 bg-white overflow-y-auto shadow-2xl">
          <div className="flex justify-between items-start mb-8">
            <div>
              <h3 className="text-4xl font-black uppercase italic leading-none tracking-tighter">{selectedProspect.name}</h3>
              <p className="text-[10px] font-bold mt-2 text-gray-400 uppercase tracking-widest border-l-2 border-gray-400 pl-2 italic">Deep Scouting Profile</p>
            </div>
            <div className="bg-black text-white p-2 font-black text-lg border-2 border-white shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">{selectedProspect.position}</div>
          </div>

          <div className="space-y-10">
            {/* AI Agent Report */}
            <div className="p-4 bg-gray-50 border-2 border-black border-dashed relative">
              <div className="absolute -top-3 left-3 bg-black text-white text-[8px] px-2 font-black italic">INTELLIGENCE REPORT</div>
              <p className="text-sm italic font-medium leading-relaxed">"{selectedProspect.report}"</p>
            </div>

            {/* Fitting Rating */}
            <section>
              <div className="flex justify-between items-end mb-2">
                <span className="text-[10px] font-black uppercase tracking-widest italic underline decoration-2">Fitting Rating</span>
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-black leading-none">{selectedProspect.rating}%</span>
                  <DeltaTag value={selectedProspect.delta} />
                </div>
              </div>
              <div className="h-6 border-4 border-black bg-white flex p-0.5 overflow-hidden">
                <div 
                  className="h-full bg-black transition-all duration-700" 
                  style={{ width: `${selectedProspect.delta >= 0 ? selectedProspect.rating - selectedProspect.delta : selectedProspect.rating - Math.abs(selectedProspect.delta)}%` }}
                ></div>
                <div 
                  className={`h-full transition-all duration-1000 ${selectedProspect.delta >= 0 ? 'bg-green-500' : 'bg-red-600'}`} 
                  style={{ width: `${Math.abs(selectedProspect.delta)}%` }}
                ></div>
              </div>
            </section>

            {/* Synergy Score */}
            <section>
              <div className="flex justify-between items-end mb-2">
                <span className="text-[10px] font-black uppercase tracking-widest italic underline decoration-2">Synergy Score</span>
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-black leading-none">{selectedProspect.synergy}%</span>
                  <DeltaTag value={selectedProspect.delta} />
                </div>
              </div>
              <div className="h-6 border-4 border-black bg-white flex p-0.5 overflow-hidden">
                <div 
                  className="h-full bg-black transition-all duration-700" 
                  style={{ width: `${selectedProspect.delta >= 0 ? selectedProspect.synergy - selectedProspect.delta : selectedProspect.synergy - Math.abs(selectedProspect.delta)}%` }}
                ></div>
                <div 
                  className={`h-full transition-all duration-1000 ${selectedProspect.delta >= 0 ? 'bg-green-500' : 'bg-red-600'}`} 
                  style={{ width: `${Math.abs(selectedProspect.delta)}%` }}
                ></div>
              </div>
            </section>

            {/* Match Stats Grid */}
            <div className="pt-8 border-t-4 border-black">
              <h4 className="text-xs font-black uppercase mb-4 tracking-widest italic underline decoration-2 underline-offset-4">Match Performance Stats</h4>
              <div className="grid grid-cols-2 gap-4">
                {[ 
                  {l: 'xG Contrib.', v: selectedProspect.stats?.xG}, 
                  {l: 'Recov/90', v: selectedProspect.stats?.recov}, 
                  {l: 'HI Sprints', v: selectedProspect.stats?.sprints}, 
                  {l: 'Pass Accuracy', v: selectedProspect.stats?.passAcc} 
                ].map((s, i) => (
                  <div key={i} className="border-2 border-black p-3 bg-gray-50 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:bg-black hover:text-white transition-colors group">
                    <p className="text-[8px] uppercase font-black opacity-40 mb-1 group-hover:opacity-100">{s.l}</p>
                    <p className="text-xl font-black italic leading-none">{s.v || '0'}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </aside>
      )}
    </div>
  );
}