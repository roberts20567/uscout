import React from 'react';

const PlayerNode = ({ player, isShadow = false, onClick }) => {
  const avatarUrl = player.img || `https://ui-avatars.com/api/?name=${encodeURIComponent(player.name)}&background=000&color=fff&bold=true&length=2`;

  return (
    <div 
      onClick={() => onClick && onClick(player)}
      className={`absolute flex flex-col items-center transition-all duration-300 
        ${isShadow ? 'z-40 scale-105' : 'z-10 hover:z-50 hover:scale-110 cursor-pointer'}`}
      style={{ left: `${player.x}%`, top: `${player.y}%`, transform: 'translate(-50%, -50%)' }}
    >
      <div className={`flex flex-col items-center shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] ${isShadow ? 'shadow-[4px_4px_0px_0px_rgba(220,38,38,1)]' : ''}`}>
        <div className={`w-11 h-11 bg-white border-2 border-black overflow-hidden relative ${isShadow ? 'border-red-600' : ''}`}>
          <img src={avatarUrl} className="w-full h-full object-cover grayscale" alt={player.name} />
          <div className="absolute top-0 right-0 bg-black text-[5px] text-white px-1 font-black py-0.5">{player.value}</div>
        </div>
        <div className={`w-full bg-white border-x-2 border-b-2 border-black py-0.5 px-1 flex flex-col items-center ${isShadow ? 'border-red-600' : ''}`}>
          <span className="text-[8px] font-black uppercase leading-none truncate w-12 text-center">{player.name.split(' ').pop()}</span>
          <span className="text-[5px] font-bold text-gray-400 leading-none mt-0.5">{player.year}</span>
        </div>
      </div>
      <div className="w-0.5 h-1.5 bg-black"></div>
      <div className="w-6 h-6 rounded-full bg-black border-2 border-white flex items-center justify-center text-[7px] font-black text-white shadow-md">
        {player.position}
      </div>
    </div>
  );
};

export default function TacticalPitch({ squad, shadowPlayer, showHeatmap, onPlayerClick }) {
  const playerToReplace = shadowPlayer 
    ? squad.find(p => p.position === shadowPlayer.position) 
    : null;

  return (
    <div className="relative w-full max-w-lg aspect-[3/4] bg-[#fcfcfc] border-4 border-black shadow-[16px_16px_0px_0px_rgba(0,0,0,1)] overflow-hidden mx-auto">
      <div className="absolute inset-4 border-2 border-black/5 pointer-events-none" />
      <div className="absolute top-1/2 left-4 right-4 h-0.5 bg-black/5 -translate-y-1/2" />
      <div className="absolute left-1/2 top-1/2 w-20 h-20 border-2 border-black/5 rounded-full -translate-x-1/2 -translate-y-1/2" />
      
      {showHeatmap && (
        <div className="absolute inset-0 pointer-events-none">
          {squad.map(p => (
            <div key={`h-${p.id}`} className="absolute w-32 h-32 bg-red-600/5 blur-[60px] rounded-full" style={{ left: `${p.x}%`, top: `${p.y}%`, transform: 'translate(-50%, -50%)' }} />
          ))}
        </div>
      )}

      {squad.map(p => {
        if (playerToReplace && p.id === playerToReplace.id) return null;
        return <PlayerNode key={p.id} player={p} onClick={onPlayerClick} />;
      })}

      {shadowPlayer && playerToReplace && (
        <PlayerNode player={{ ...shadowPlayer, x: playerToReplace.x, y: playerToReplace.y }} isShadow={true} />
      )}
      <div className="absolute bottom-6 right-6 opacity-5 font-black italic text-2xl tracking-tighter select-none uppercase">USCOUT</div>
    </div>
  );
}