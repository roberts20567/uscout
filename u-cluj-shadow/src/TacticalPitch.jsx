import React from 'react';

const PlayerNode = ({ player, isShadow = false, showHeatmap = false, onClick }) => {
  const avatarUrl = player.img || `https://ui-avatars.com/api/?name=${encodeURIComponent(player.name)}&background=000&color=fff&bold=true&length=2`;

  let haloClass = '';
  if (showHeatmap && !isShadow && player.deficit !== undefined) {
    if (player.deficit > 0.7) haloClass = 'bg-red-600 shadow-[0_0_30px_10px_rgba(220,38,38,0.9)] border-4 border-black animate-pulse scale-125';
    else if (player.deficit > 0.4) haloClass = 'bg-yellow-300 shadow-[0_0_20px_10px_rgba(253,224,71,0.9)] border-4 border-black animate-pulse scale-110';
    else haloClass = 'bg-green-500 shadow-[0_0_15px_5px_rgba(34,197,94,0.4)] opacity-80 border-4 border-black scale-105';
  }

  return (
    <div 
      onClick={() => onClick && onClick(player)}
      className={`absolute flex flex-col items-center transition-all duration-300 
        ${isShadow ? 'z-40 scale-105' : 'z-10 hover:z-50 hover:scale-110 cursor-pointer'} group`}
      style={{ left: `${player.x}%`, top: `${player.y}%`, transform: 'translate(-50%, -50%)' }}
    >
      {/* Brutalist Heatmap Halo Overlay */}
      {showHeatmap && !isShadow && (
        <div className={`absolute inset-0 -z-10 transition-all duration-500 ${haloClass}`}></div>
      )}

      {/* Main Card Body */}
      <div className={`relative flex flex-col items-center bg-white border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] group-hover:shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] transition-shadow ${isShadow ? 'border-red-600 shadow-[4px_4px_0px_0px_rgba(220,38,38,1)] group-hover:shadow-[6px_6px_0px_0px_rgba(220,38,38,1)]' : ''}`}>
        
        {/* Rating Badge - Popping out of top right */}
        <div className={`absolute -top-3 -right-3 border-2 border-black text-[10px] font-black px-1.5 py-0.5 z-20 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${isShadow ? 'bg-red-600 text-white' : 'bg-yellow-300 text-black'}`}>
          {player.value}
        </div>

        {/* Player Image */}
        <div className={`w-12 h-12 overflow-hidden bg-gray-100 ${isShadow ? 'opacity-90' : ''}`}>
          <img src={avatarUrl} className="w-full h-full object-cover grayscale contrast-125" alt={player.name} />
        </div>

        {/* Player Name */}
        <div className={`w-full border-t-2 border-black py-1 px-1 flex flex-col items-center justify-center ${isShadow ? 'bg-red-50' : 'bg-white'}`}>
          <span className="text-[9px] font-black uppercase tracking-tighter truncate w-14 text-center text-black antialiased leading-none">
            {player.name.split(' ').pop()}
          </span>
        </div>
      </div>

      {/* Connector */}
      <div className={`w-1 h-1.5 ${isShadow ? 'bg-red-600' : 'bg-black'}`}></div>

      {/* Position Label */}
      <div className={`px-2 py-0.5 border-2 border-black flex items-center justify-center text-[8px] font-black uppercase tracking-widest shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${isShadow ? 'bg-red-600 text-white' : 'bg-black text-white'}`}>
        {player.position}
      </div>
    </div>
  );
};

export default function TacticalPitch({ squad, shadowPlayer, showHeatmap, onPlayerClick }) {
  const playerToReplace = shadowPlayer 
    ? squad.find(p => shadowPlayer.replaceId ? p.id === shadowPlayer.replaceId : p.position === shadowPlayer.position) 
    : null;

  return (
    <div className="relative w-full max-w-lg aspect-[3/4] bg-[#fcfcfc] border-4 border-black shadow-[16px_16px_0px_0px_rgba(0,0,0,1)] overflow-hidden mx-auto">
      {/* --- PITCH MARKINGS --- */}
      <div className="absolute inset-4 border-2 border-black/20 pointer-events-none">
        {/* Center Line */}
        <div className="absolute top-1/2 left-0 right-0 h-[2px] bg-black/20 -translate-y-1/2" />
        
        {/* Center Circle & Spot */}
        <div className="absolute left-1/2 top-1/2 w-24 h-24 border-2 border-black/20 rounded-full -translate-x-1/2 -translate-y-1/2" />
        <div className="absolute left-1/2 top-1/2 w-1.5 h-1.5 bg-black/20 rounded-full -translate-x-1/2 -translate-y-1/2" />

        {/* Top Half Markings */}
        <div className="absolute top-[15%] left-1/2 w-24 h-12 border-2 border-t-0 border-black/20 rounded-b-full -translate-x-1/2" />
        <div className="absolute top-0 left-1/2 w-[60%] h-[15%] border-2 border-t-0 border-black/20 -translate-x-1/2 bg-[#fcfcfc]" /> 
        <div className="absolute top-0 left-1/2 w-[26%] h-[5%] border-2 border-t-0 border-black/20 -translate-x-1/2" />
        <div className="absolute -top-[10px] left-1/2 w-[16%] h-[10px] border-2 border-b-0 border-black/20 -translate-x-1/2" />

        {/* Bottom Half Markings */}
        <div className="absolute bottom-[15%] left-1/2 w-24 h-12 border-2 border-b-0 border-black/20 rounded-t-full -translate-x-1/2" />
        <div className="absolute bottom-0 left-1/2 w-[60%] h-[15%] border-2 border-b-0 border-black/20 -translate-x-1/2 bg-[#fcfcfc]" />
        <div className="absolute bottom-0 left-1/2 w-[26%] h-[5%] border-2 border-b-0 border-black/20 -translate-x-1/2" />
        <div className="absolute -bottom-[10px] left-1/2 w-[16%] h-[10px] border-2 border-t-0 border-black/20 -translate-x-1/2" />
      </div>
      
      {squad.map(p => {
        if (playerToReplace && p.id === playerToReplace.id) return null;
        return <PlayerNode key={p.id} player={p} showHeatmap={showHeatmap} onClick={onPlayerClick} />;
      })}

      {shadowPlayer && playerToReplace && (
        <PlayerNode player={{ ...shadowPlayer, x: playerToReplace.x, y: playerToReplace.y }} isShadow={true} />
      )}
      <div className="absolute bottom-6 right-6 opacity-5 font-black italic text-2xl tracking-tighter select-none uppercase">USCOUT</div>
    </div>
  );
}