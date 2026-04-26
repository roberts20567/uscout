import React, { useState, useEffect } from 'react';
import TacticalPitch from './TacticalPitch';
import { collection, getDocs, getDoc, doc, setDoc, onSnapshot, addDoc, deleteDoc, serverTimestamp, query, orderBy, where } from 'firebase/firestore';
import { db } from './firebase'; // Ensure you have your Firebase client initialized here

// Utility for performance indicators (Green for growth, Red for risk, Gray for neutral)
const getDeltaStyling = (value) => {
  if (value > 0) return { text: `+${value}%`, colorClass: 'bg-green-500 text-white', textClass: 'text-green-500' };
  if (value < 0) return { text: `${value}%`, colorClass: 'bg-red-600 text-white', textClass: 'text-red-600' };
  return { text: `0%`, colorClass: 'bg-gray-400 text-white', textClass: 'text-gray-400' };
};

const DeltaTag = ({ value }) => {
  if (value === 0) return null; // Hides the badge cleanly if there is no change
  const { text, colorClass } = getDeltaStyling(value);
  return (
    <span className={`text-[10px] font-black px-1 ${colorClass}`}>
      {text}
    </span>
  );
};

// Utility to format stat labels (add custom mappings here)
const formatStatLabel = (key) => {
  const map = { 'Accurate Passes Percentage': 'Pass Accuracy %' };
  return map[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

// Utility to format stat numerical values
const formatStatValue = (val) => {
  if (typeof val === 'number') return Number.isInteger(val) ? val : parseFloat(val.toFixed(2));
  return val ?? '-';
};

// Determines which stats matter most based on position acronyms
const getPriorityKeywords = (pos = '') => {
  const p = pos.toUpperCase();
  if (['ST', 'CF', 'LW', 'RW', 'AM', 'FW'].some(k => p.includes(k))) {
    return ['GOAL', 'ASSIST', 'XG', 'SHOT', 'DRIBBLE', 'KEY PASS', 'ATTACK'];
  }
  if (['CM', 'CDM', 'LM', 'RM'].some(k => p.includes(k))) {
    return ['PASS', 'ASSIST', 'RECOVER', 'INTERCEPT', 'THIRD', 'DUEL'];
  }
  if (['CB', 'LB', 'RB', 'LWB', 'RWB', 'DEFENDER'].some(k => p.includes(k))) {
    return ['DUEL', 'AERIAL', 'INTERCEPT', 'RECOVER', 'CLEAR', 'TACKLE'];
  }
  if (['GK', 'GOALKEEPER'].some(k => p.includes(k))) {
    return ['SAVE', 'CLEAN SHEET', 'CONCEDED', 'REFLEX'];
  }
  return ['GOAL', 'ASSIST', 'PASS', 'DUEL']; // Fallback
};

// Sorts the object into an ordered array based on the priority keywords
const sortStatsByPosition = (statsObj, position) => {
  if (!statsObj) return [];
  const keywords = getPriorityKeywords(position);
  
  return Object.entries(statsObj).sort(([keyA], [keyB]) => {
    const scoreA = keywords.findIndex(kw => keyA.toUpperCase().includes(kw));
    const scoreB = keywords.findIndex(kw => keyB.toUpperCase().includes(kw));
    return (scoreA !== -1 ? scoreA : 999) - (scoreB !== -1 ? scoreB : 999) || keyA.localeCompare(keyB);
  });
};

// Multiple tactical blueprints
const FORMATIONS = {
  '4-2-3-1': [
    { roleId: 'GK', position: 'GK', x: 50, y: 92 },
    { roleId: 'LB', position: 'LB', x: 15, y: 75 },
    { roleId: 'LCB', position: 'CB', x: 38, y: 80 },
    { roleId: 'RCB', position: 'CB', x: 62, y: 80 },
    { roleId: 'RB', position: 'RB', x: 85, y: 75 },
    { roleId: 'LCM', position: 'CM', x: 40, y: 60 },
    { roleId: 'RCM', position: 'CM', x: 60, y: 60 },
    { roleId: 'LW', position: 'LW', x: 20, y: 38 },
    { roleId: 'AM', position: 'AM', x: 50, y: 45 },
    { roleId: 'RW', position: 'RW', x: 80, y: 38 },
    { roleId: 'ST', position: 'ST', x: 50, y: 18 }
  ],
  '4-3-3': [
    { roleId: 'GK', position: 'GK', x: 50, y: 92 },
    { roleId: 'LB', position: 'LB', x: 15, y: 75 },
    { roleId: 'LCB', position: 'CB', x: 38, y: 80 },
    { roleId: 'RCB', position: 'CB', x: 62, y: 80 },
    { roleId: 'RB', position: 'RB', x: 85, y: 75 },
    { roleId: 'LCM', position: 'CM', x: 30, y: 60 },
    { roleId: 'CM', position: 'CM', x: 50, y: 65 },
    { roleId: 'RCM', position: 'CM', x: 70, y: 60 },
    { roleId: 'LW', position: 'LW', x: 20, y: 25 },
    { roleId: 'ST', position: 'ST', x: 50, y: 18 },
    { roleId: 'RW', position: 'RW', x: 80, y: 25 }
  ],
  '4-4-2': [
    { roleId: 'GK', position: 'GK', x: 50, y: 92 },
    { roleId: 'LB', position: 'LB', x: 15, y: 75 },
    { roleId: 'LCB', position: 'CB', x: 38, y: 80 },
    { roleId: 'RCB', position: 'CB', x: 62, y: 80 },
    { roleId: 'RB', position: 'RB', x: 85, y: 75 },
    { roleId: 'LM', position: 'LM', x: 15, y: 55 },
    { roleId: 'LCM', position: 'CM', x: 40, y: 60 },
    { roleId: 'RCM', position: 'CM', x: 60, y: 60 },
    { roleId: 'RM', position: 'RM', x: 85, y: 55 },
    { roleId: 'LST', position: 'ST', x: 40, y: 20 },
    { roleId: 'RST', position: 'ST', x: 60, y: 20 }
  ]
};

const getRoleKeywords = (pos) => {
  if (pos.includes('GK')) return ['GOALKEEPER', 'GK'];
  if (pos.includes('CB')) return ['CENTER_BACK', 'CB', 'DEFENDER'];
  if (pos.includes('LB') || pos.includes('LWB')) return ['LEFT', 'BACK', 'FULLBACK', 'DEFENDER'];
  if (pos.includes('RB') || pos.includes('RWB')) return ['RIGHT', 'BACK', 'FULLBACK', 'DEFENDER'];
  if (pos.includes('LM') || pos.includes('RM') || pos.includes('W')) return ['WINGER', 'WG', 'MIDFIELDER'];
  if (pos === 'CDM' || pos.includes('CM')) return ['MIDFIELDER', 'MD'];
  if (pos === 'AM') return ['ATTACKING MIDFIELDER', 'MIDFIELDER'];
  return ['ATTACKER', 'STRIKER', 'FW', 'FORWARD', 'CF'];
};

export default function App() {
  // --- CORE STATE ---
  const [view, setView] = useState('home'); 
  const [isLoadingBoard, setIsLoadingBoard] = useState(true);
  const [projects, setProjects] = useState([]);
  const [activeProject, setActiveProject] = useState(null);
  const [selectedProspect, setSelectedProspect] = useState(null);
  const [heatmap, setHeatmap] = useState(false);
  const [squad, setSquad] = useState(FORMATIONS['4-2-3-1'].map(pos => ({ ...pos, id: pos.roleId, name: "Loading...", value: "-", rating: 0, synergy: 0, year: "-" })));
  const [liveProspects, setLiveProspects] = useState({});
  const [squadDeficits, setSquadDeficits] = useState({});
  
  // --- TEAM EDITING STATE ---
  const [allTeamPlayers, setAllTeamPlayers] = useState([]);
  const [activeFormation, setActiveFormation] = useState('4-2-3-1');
  const [backupSquad, setBackupSquad] = useState([]);
  const [editTargetPlayer, setEditTargetPlayer] = useState(null);

  // --- MODAL / SCOUTING STATE ---
  const [targetPlayer, setTargetPlayer] = useState(null);
  const [selectedPoolIds, setSelectedPoolIds] = useState([]);
  const [scoutedProspects, setScoutedProspects] = useState([]);
  const [isScouting, setIsScouting] = useState(false);
  const [flashReport, setFlashReport] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState('');

  // Function to map real players to a given formation blueprint
  const buildSquad = (formationKey, playersList) => {
    const assignedIds = new Set();

    const getBestPlayerForRole = (roleKeywords) => {
      const player = playersList.find(p => 
        !assignedIds.has(p.player_id) && 
        roleKeywords.some(kw => p.position && p.position.toUpperCase().includes(kw))
      );
      if (player) {
        assignedIds.add(player.player_id);
        return player;
      }
      const fallback = playersList.find(p => !assignedIds.has(p.player_id));
      if (fallback) assignedIds.add(fallback.player_id);
      return fallback;
    };

    return FORMATIONS[formationKey].map(template => {
      const roleKeywords = getRoleKeywords(template.roleId.toUpperCase());
      const bestPlayer = getBestPlayerForRole(roleKeywords);

      if (bestPlayer) {
        return {
          ...template,
          id: bestPlayer.player_id,
          name: bestPlayer.name,
          value: bestPlayer.base_bpi ? Math.round(bestPlayer.base_bpi) : "-",
          rating: bestPlayer.dynamic_rating || bestPlayer.base_bpi || 0,
          synergy: bestPlayer.synergy_score || 0,
          year: '24/25'
        };
      }
      return { ...template, id: template.roleId, name: "Empty", value: "-", rating: 0, synergy: 0, year: "-" };
    });
  };

  // --- 1. FETCH PLAYERS FROM FIREBASE ---
  useEffect(() => {
    const fetchPlayers = async () => {
      try {
        const querySnapshot = await getDocs(collection(db, 'u_players_calculated'));
        const players = [];
        querySnapshot.forEach(docSnap => {
          const data = docSnap.data();
          // Only pick players whose ID starts with "U" (U Cluj players)
          if (data.player_id && String(data.player_id).startsWith('U')) {
            players.push(data);
          }
        });

        // Sort players by Minutes Played descending
        players.sort((a, b) => {
          const minsA = a.key_stats_used?.['Minutes Played'] || 0;
          const minsB = b.key_stats_used?.['Minutes Played'] || 0;
          return minsB - minsA;
        });

        setAllTeamPlayers(players);
      } catch (err) {
        console.error("Failed to load U Cluj players:", err);
      }
    };
    fetchPlayers();
  }, []);

  // --- 2. LISTEN TO PROJECTS LIST ---
  useEffect(() => {
    const q = query(collection(db, 'projects'), orderBy('createdAt', 'desc'));
    const unsub = onSnapshot(q, (snap) => {
      const projs = snap.docs.map(d => ({ id: d.id, ...d.data() }));
      setProjects(projs);
    });
    return () => unsub();
  }, []);

  // --- 3. LISTEN TO ACTIVE BOARD (GLOBAL OR SPECIFIC PROJECT) ---
  useEffect(() => {
    if (allTeamPlayers.length === 0) return;

    setIsLoadingBoard(true);
    const docRef = activeProject?.id ? doc(db, 'projects', activeProject.id) : doc(db, 'webpage_uscout', 'current_team');

    const unsub = onSnapshot(docRef, (docSnap) => {
      if (docSnap.exists()) {
        const data = docSnap.data();
        // Projects nest the tactical data inside "formationData", while global uses the root
        const boardData = (activeProject?.id && data.formationData) ? data.formationData : data;
        
        setActiveFormation(prev => prev !== boardData.formation ? (boardData.formation || '4-2-3-1') : prev);
        
        if (boardData.players) {
          const reconstructedSquad = boardData.players.map(p => {
            const realPlayer = allTeamPlayers.find(rp => rp.player_id === p.player_id);
            if (realPlayer) {
              return {
                roleId: p.roleId,
                position: p.position,
                x: p.x,
                y: p.y,
                id: p.player_id,
                name: realPlayer.name,
                value: realPlayer.base_bpi ? Math.round(realPlayer.base_bpi) : "-",
                rating: realPlayer.dynamic_rating || realPlayer.base_bpi || 0,
                synergy: realPlayer.synergy_score || 0,
                year: '24/25'
              };
            }
            return {
              roleId: p.roleId,
              position: p.position,
              x: p.x,
              y: p.y,
              id: p.roleId,
              name: "Empty",
              value: "-",
              rating: 0,
              synergy: 0,
              year: "-"
            };
          });
          
          setSquad(prev => {
            const isDiff = JSON.stringify(prev) !== JSON.stringify(reconstructedSquad);
            return isDiff ? reconstructedSquad : prev;
          });
        }
      } else {
        // Fallback if no tactical board is saved yet
        const defaultSquad = buildSquad('4-2-3-1', allTeamPlayers);
        setSquad(prev => {
          const isDiff = JSON.stringify(prev) !== JSON.stringify(defaultSquad);
          return isDiff ? defaultSquad : prev;
        });
      }
      setIsLoadingBoard(false);
    }, (err) => {
      console.error("Failed to load tactical board from Firebase:", err);
      setIsLoadingBoard(false);
    });

    return () => unsub();
  }, [activeProject?.id, allTeamPlayers]);

  // --- FIRESTORE SYNC (DEBOUNCED) ---
  useEffect(() => {
    if (isLoadingBoard) return; // Prevent overwriting Firebase with default state during initial load

    const syncTacticalBoard = async () => {
      try {
        const payloadPlayers = squad.map(p => ({
          roleId: p.roleId,
          position: p.position,
          player_id: p.id, // Matches the uid player requirement
          x: p.x,
          y: p.y
        }));

        if (activeProject?.id) {
          const docRef = doc(db, 'projects', activeProject.id);
          await setDoc(docRef, {
            formationData: { formation: activeFormation, players: payloadPlayers }
          }, { merge: true });
        } else {
          const docRef = doc(db, 'webpage_uscout', 'current_team');
          await setDoc(docRef, {
            formation: activeFormation,
            players: payloadPlayers
          }, { merge: true });
        }
      } catch (err) {
        console.error('Error saving tactical board to Firestore:', err);
      }
    };

    // Debounce the save operation by 1 second to avoid excessive writes
    const debounceTimer = setTimeout(() => {
      syncTacticalBoard();
    }, 1000);

    // Cleanup timer if squad/formation changes before the 1 second is up
    return () => clearTimeout(debounceTimer);
  }, [squad, activeFormation, activeProject?.id, isLoadingBoard]);

  // --- 3.5 REAL-TIME SYNC FOR ACTIVE PROJECT PROSPECTS ---
  useEffect(() => {
    if (view === 'project' && activeProject?.prospects?.length > 0) {
      const prospectIds = activeProject.prospects.map(p => String(p.id)).slice(0, 10);
      
      if (prospectIds.length === 0) return;

      const q = query(collection(db, 'u_dynamic_shadow_prospects'), where('__name__', 'in', prospectIds));
      const unsub = onSnapshot(q, (snap) => {
        const liveData = {};
        snap.forEach(docSnap => {
          const data = docSnap.data();
          liveData[docSnap.id] = {
            ...data,
            _rating: data['Dynamic Rating'] ?? data.dynamicRating ?? data.rating ?? data.dynamic_rating ?? data.Dynamic_Rating ?? 0,
            _synergy: data['Synergy'] ?? data.synergy ?? data.Synergy_Score ?? data.synergy_score ?? 0,
          };
        });
        setLiveProspects(liveData);
      });
      return () => unsub();
    } else {
      setLiveProspects({});
    }
  }, [activeProject, view]);

  // --- SEARCH DEBOUNCE ---
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearchTerm(searchTerm), 500);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  // --- 4. DYNAMIC SCOUTING FETCH ---
  useEffect(() => {
    if (!targetPlayer) {
      setScoutedProspects([]);
      setSelectedPoolIds([]);
      setSearchTerm('');
      return;
    }

    const fetchProspects = async () => {
      setIsScouting(true);
      try {
        let q;
        if (debouncedSearchTerm.trim() !== '') {
          // Format string properly (e.g., "ioan" -> "Ioan") to match Firestore's case-sensitivity
          const searchVal = debouncedSearchTerm.trim().split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ');
          q = query(
            collection(db, 'u_dynamic_shadow_prospects'),
            where('name', '>=', searchVal),
            where('name', '<=', searchVal + '\uf8ff')
          );
        } else {
          q = query(collection(db, 'u_dynamic_shadow_prospects'));
        }
        const snap = await getDocs(q);
        const keywords = getRoleKeywords(targetPlayer.roleId.toUpperCase());

        let prospects = [];
        snap.forEach(docSnap => {
          const data = docSnap.data();
          // Debugging: View raw Firebase data to verify field names
          console.log(`Raw Firebase Data for ${docSnap.id}:`, data);
          const pos = data.position ? data.position.toUpperCase() : '';
          // Simple filter by position keywords
          
          // Normalize keys using fallbacks to handle different potential Firestore naming conventions
          const ratingVal = data['Dynamic Rating'] ?? data.dynamicRating ?? data.rating ?? data.dynamic_rating ?? data.Dynamic_Rating ?? 0;
          const synergyVal = data['Synergy'] ?? data.synergy ?? data.Synergy_Score ?? data.synergy_score ?? 0;

          // Ignore position filter when a specific name search is active
          if (debouncedSearchTerm.trim() !== '' || keywords.some(kw => pos.includes(kw))) {
            prospects.push({ id: docSnap.id, ...data, _rating: ratingVal, _synergy: synergyVal });
          }
        });

        // Sort by combined score (Rating + Synergy)
        prospects.sort((a, b) => {
          const scoreA = a._rating + a._synergy;
          const scoreB = b._rating + b._synergy;
          return scoreB - scoreA;
        });

        // Take top 10
        const top10 = prospects.slice(0, 10);

        // API Integration: Transfermarkt (Optimized to only fetch for top 10)
        // Replace TM_API_URL with your hosted Transfermarkt API endpoint!
        const TM_API_URL = 'http://localhost:3000';
        const augmented = await Promise.all(top10.map(async (p) => {
          try {
            const searchRes = await fetch(`${TM_API_URL}/players/search/${encodeURIComponent(p.name)}`);
            if (searchRes.ok) {
              const searchData = await searchRes.json();
              const firstResult = searchData.results?.[0] || searchData[0];
              
              if (firstResult && firstResult.id) {
                // Fetch full profile to get detailed metrics like foot and height
                const profileRes = await fetch(`${TM_API_URL}/players/${firstResult.id}/profile`);
                if (profileRes.ok) {
                  const profileData = await profileRes.json();
                  return { 
                    ...p, 
                    marketValue: profileData.marketValue || firstResult.marketValue || 'N/A', 
                    age: profileData.age || firstResult.age || '-',
                    foot: profileData.foot || '-',
                    height: profileData.height || '-'
                  };
                }
                
                // Fallback to basic search data if profile fetch fails
                return { 
                  ...p, 
                  marketValue: firstResult.marketValue || 'N/A', 
                  age: firstResult.age || '-',
                  foot: '-',
                  height: '-'
                };
              }
            }
          } catch(err) {
            console.warn(`TM API fetch failed for ${p.name}`, err);
          }
          return { ...p, marketValue: 'N/A', age: '-' };
        }));

        setScoutedProspects(augmented);
      } catch (err) {
        console.error("Error fetching prospects:", err);
      } finally {
        setIsScouting(false);
      }
    };

    fetchProspects();
  }, [targetPlayer, debouncedSearchTerm]);

  // --- 4.5 HEATMAP DEFICITS FETCH ---
  useEffect(() => {
    let unsub = () => {};

    if (heatmap) {
      try {
        const docRef = doc(db, 'u_config', 'squad_deficits');
        unsub = onSnapshot(docRef, (snap) => {
          if (snap.exists()) {
            setSquadDeficits(snap.data());
          }
        });
      } catch (err) {
        console.error("Error listening to squad deficits:", err);
      }
    }
    return () => unsub();
  }, [heatmap]);

  // Calculate deficit helper inside App
  const getPlayerDeficit = (roleId) => {
    if (!squadDeficits || Object.keys(squadDeficits).length === 0) return 0;
    const kws = getRoleKeywords(roleId.toUpperCase());
    for (let kw of kws) {
      if (squadDeficits[kw] !== undefined) return squadDeficits[kw];
    }
    return 0;
  };

  // --- 4.6 REPORT FLASH EFFECT ---
  const activeReportText = view === 'project' && selectedProspect 
    ? (liveProspects[selectedProspect.id]?.reason || selectedProspect.reason) 
    : null;

  useEffect(() => {
    if (activeReportText) {
      setFlashReport(true);
      const t = setTimeout(() => setFlashReport(false), 1500);
      return () => clearTimeout(t);
    }
  }, [activeReportText]);

  // --- HANDLERS ---
  const createNewProject = async (name, additionalData = {}) => {
    const payloadPlayers = squad.map(p => ({
      roleId: p.roleId, position: p.position, player_id: p.id, x: p.x, y: p.y
    }));
    
    const newProj = {
      projectName: name,
      createdAt: serverTimestamp(),
      formationData: {
        formation: activeFormation,
        players: payloadPlayers
      },
      ...additionalData
    };

    try {
      await addDoc(collection(db, 'projects'), newProj);
    } catch(e) { 
      console.error('Failed to create project:', e); 
    }
  };

  const handleCreateProjectFromModal = () => {
    const selectedProspects = scoutedProspects.filter(p => selectedPoolIds.includes(p.id)).map(p => ({
      ...p,
      initial_dynamic_rating: p._rating || 0,
      initial_synergy_score: p._synergy || 0
    }));
    const name = `${targetPlayer.position} UPGRADE: ${targetPlayer.name.split(' ').pop()}`;
    
    createNewProject(name, {
      description: `Targeting replacements for ${targetPlayer.name}`,
      prospects: selectedProspects,
      replacedPlayer: {
        ...targetPlayer,
        initial_dynamic_rating: targetPlayer.rating || 0,
        initial_synergy_score: targetPlayer.synergy || 0
      }
    });
    
    setTargetPlayer(null);
    setSelectedPoolIds([]);
    setSearchTerm('');
  };

  const loadProject = (proj) => {
    setActiveProject(proj);
    setView('project');
    if (proj.prospects && proj.prospects.length > 0) {
      setSelectedProspect(proj.prospects[0]);
    } else {
      setSelectedProspect(null);
    }
  };

  const handleDeleteProject = async (e, id) => {
    e.stopPropagation(); // Stops the project from opening when clicking delete
    if (window.confirm("Confirm: Delete this scouting project?")) {
      await deleteDoc(doc(db, 'projects', id));
      if (activeProject?.id === id) {
        setActiveProject(null);
        setView('home');
      }
    }
  };

  const handleSwapPlayer = (newPlayer) => {
    const updatedSquad = squad.map(p => {
      if (p.roleId === editTargetPlayer.roleId) {
        return {
          ...p,
          id: newPlayer.player_id,
          name: newPlayer.name,
          value: newPlayer.base_bpi ? Math.round(newPlayer.base_bpi) : "-"
        };
      }
      return p;
    });
    setSquad(updatedSquad);
    setEditTargetPlayer(null); // Deselect after swap
  };

  if (isLoadingBoard) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-[#fdfdfd] font-sans text-black">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-black border-t-transparent rounded-full animate-spin"></div>
          <h2 className="text-xl font-black uppercase italic tracking-widest">Loading Tactical Board...</h2>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-white font-sans text-black overflow-hidden relative">
      
      {/* --- 1. SCOUTING MODAL (MULTI-SELECT) --- */}
      {targetPlayer && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-md p-4">
          <div className="bg-white border-4 border-black shadow-[16px_16px_0px_0px_rgba(0,0,0,1)] w-full max-w-4xl p-8 flex flex-col max-h-[85vh]">
            <div className="flex justify-between items-start mb-6 border-b-4 border-black pb-4">
              <div>
                <h2 className="text-3xl font-black uppercase italic tracking-tighter">Scout: {targetPlayer.position}</h2>
                <p className="text-xs font-bold text-gray-500 uppercase tracking-widest mt-1">Simulating Top 10 Prospects for {targetPlayer.name}</p>
              </div>
              <button onClick={() => { setTargetPlayer(null); setSearchTerm(''); }} className="font-black text-2xl hover:scale-125 transition-transform">✕</button>
            </div>

            {/* SEARCH BAR */}
            <div className="mb-6 flex gap-2">
              <input 
                type="text" 
                placeholder="SEARCH PROSPECTS BY NAME..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="flex-1 p-3 border-4 border-black font-black uppercase italic tracking-widest outline-none focus:bg-yellow-300 transition-colors"
              />
              {searchTerm && (
                <button 
                  onClick={() => setSearchTerm('')}
                  className="px-6 py-3 bg-black text-white border-4 border-black font-black uppercase tracking-widest hover:bg-red-600 transition-colors"
                >
                  Clear
                </button>
              )}
            </div>

            {isScouting ? (
              <div className="flex-1 flex flex-col items-center justify-center min-h-[300px]">
                <div className="w-16 h-16 border-4 border-black border-t-transparent rounded-full animate-spin"></div>
                <p className="mt-6 font-black uppercase tracking-widest animate-pulse">Running AI Scout Search...</p>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto space-y-4 pr-2">
                {scoutedProspects.map(p => {
                  const isChecked = selectedPoolIds.includes(p.id);
                  return (
                    <div 
                      key={p.id}
                      onClick={() => setSelectedPoolIds(prev => isChecked ? prev.filter(id => id !== p.id) : [...prev, p.id])}
                      className={`p-4 border-4 border-black cursor-pointer grid grid-cols-6 gap-4 items-center transition-all ${isChecked ? 'bg-black text-white translate-x-1 translate-y-1 shadow-none' : 'bg-white shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:bg-gray-50'}`}
                    >
                      <div className="col-span-2 flex flex-col">
                        <span className="text-lg font-black uppercase tracking-tight truncate">{p.name}</span>
                        <span className="text-[10px] opacity-60 font-bold uppercase tracking-widest">{p.position} • Age: {p.age}</span>
                      </div>
                      <div className="flex flex-col items-center">
                        <span className="text-[10px] opacity-60 font-bold uppercase tracking-widest text-center">Dyn. Rating</span>
                        <span className="text-2xl font-black italic">{p._rating || 0}</span>
                      </div>
                      <div className="flex flex-col items-center">
                        <span className="text-[10px] opacity-60 font-bold uppercase tracking-widest text-center">Synergy</span>
                        <span className="text-2xl font-black italic">{p._synergy || 0}</span>
                      </div>
                      <div className="flex flex-col items-end pr-4">
                        <span className="text-[10px] opacity-60 font-bold uppercase tracking-widest text-right">Market Value</span>
                        <span className="text-lg font-black">{p.marketValue}</span>
                      </div>
                      <div className="flex justify-end items-center pr-2">
                        <div className={`w-8 h-8 border-4 border-current flex items-center justify-center font-black ${isChecked ? 'bg-green-500' : ''}`}>
                          {isChecked && '✓'}
                        </div>
                      </div>
                    </div>
                  );
                })}
                {scoutedProspects.length === 0 && !isScouting && (
                  <p className="text-center font-bold text-gray-400 italic mt-10 uppercase tracking-widest">No suitable prospects found in database.</p>
                )}
              </div>
            )}

            <button 
              disabled={selectedPoolIds.length === 0 || isScouting} 
              onClick={handleCreateProjectFromModal} 
              className="mt-6 w-full p-4 bg-black text-white font-black uppercase italic border-4 border-black hover:bg-white hover:text-black disabled:opacity-20 transition-all text-xl"
            >
              Start Project ({selectedPoolIds.length} Targets)
            </button>
          </div>
        </div>
      )}

      {/* --- 2. LEFT SIDEBAR (NAVIGATION & ACTIVE PROJECTS) --- */}
      {view === 'edit_team' ? (
        <aside className="order-last w-80 border-l-4 border-black p-6 bg-yellow-300 flex flex-col z-10">
          <h2 className="text-3xl font-black uppercase mb-2 italic tracking-tighter text-black">EDIT MODE</h2>
          <p className="text-[10px] font-bold text-black/60 uppercase mb-8 tracking-widest border-b-2 border-black pb-2">Modify Tactics</p>
          
          <div className="space-y-4 flex-1">
            <button 
              onClick={() => {
                const formations = Object.keys(FORMATIONS);
                const nextIdx = (formations.indexOf(activeFormation) + 1) % formations.length;
                const nextForm = formations[nextIdx];
                setActiveFormation(nextForm);
                setSquad(buildSquad(nextForm, allTeamPlayers));
                setEditTargetPlayer(null);
              }} 
              className="w-full p-4 border-4 border-black bg-white font-black uppercase shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all text-sm"
            >
              Change Form: {activeFormation}
            </button>
          </div>

          <div className="space-y-4 mt-auto">
            <button 
              onClick={() => {
                setView('home');
                setEditTargetPlayer(null);
              }} 
              className="w-full p-4 bg-black text-white font-black uppercase border-4 border-black hover:bg-white hover:text-black transition-all"
            >
              Done
            </button>
            <button 
              onClick={() => {
                setSquad(backupSquad);
                setView('home');
                setEditTargetPlayer(null);
              }} 
              className="w-full p-4 bg-white text-red-600 font-black uppercase border-4 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:bg-red-600 hover:text-white hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
            >
              Cancel
            </button>
          </div>
        </aside>
      ) : (
        <aside className="w-80 border-r-4 border-black p-6 bg-gray-50 flex flex-col z-10">
          <h2 className="text-5xl font-black uppercase mb-8 italic tracking-tighter select-none">USCOUT</h2>
          
          {view === 'home' ? (
            <>
              <button 
                onClick={() => setHeatmap(!heatmap)} 
                className={`w-full mb-4 p-3 border-4 border-black font-black uppercase text-xs shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] active:translate-x-1 active:translate-y-1 active:shadow-none transition-all ${heatmap ? 'bg-red-600 text-white border-red-600' : 'bg-white'}`}
              >
                {heatmap ? 'Deactivate Heatmap' : 'Analyze Team Heatmap'}
              </button>
              
              {heatmap ? (
                <div className="mb-6 border-4 border-black p-3 bg-white">
                  <p className="text-[10px] font-black uppercase text-black mb-2 tracking-widest border-b-2 border-black pb-1">Change Necessity</p>
                  <div className="flex justify-between items-center gap-2 text-[8px] font-black uppercase tracking-tighter">
                    <div className="flex-1 flex flex-col items-center">
                      <div className="w-full h-3 bg-green-500 shadow-[0_0_10px_2px_rgba(34,197,94,0.4)] mb-1 border-2 border-black"></div>
                      <span>Low (0-0.4)</span>
                    </div>
                    <div className="flex-1 flex flex-col items-center">
                      <div className="w-full h-3 bg-yellow-300 shadow-[0_0_10px_2px_rgba(253,224,71,0.8)] mb-1 border-2 border-black"></div>
                      <span>Med (0.4-0.7)</span>
                    </div>
                    <div className="flex-1 flex flex-col items-center">
                      <div className="w-full h-3 bg-red-600 shadow-[0_0_15px_2px_rgba(220,38,38,0.8)] mb-1 border-2 border-black"></div>
                      <span>High (0.7-1.0)</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="mb-6 bg-yellow-300 border-2 border-black p-2 text-[9px] font-black uppercase animate-pulse text-center">
                  Click player on field to scout
                </div>
              )}

              <p className="text-[10px] font-black uppercase text-gray-400 mb-4 tracking-widest border-b-2 border-gray-200 pb-2">Active Projects</p>
              
              {activeProject && (
                <button onClick={() => setActiveProject(null)} className="w-full mb-4 p-3 bg-black text-white font-black uppercase text-xs shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] active:translate-x-1 active:translate-y-1 active:shadow-none transition-all">
                  View Global Team
                </button>
              )}
              
              <div className="space-y-6 overflow-y-auto pr-4 py-4">
                {projects.map(proj => (
                  <div key={proj.id} className="relative">
                    <button 
                      onClick={() => loadProject(proj)} 
                      className={`w-full text-left p-4 border-[4px] border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:bg-black hover:text-white transition-all ${activeProject?.id === proj.id ? 'bg-black text-white' : 'bg-white'}`}
                    >
                      <h3 className="font-black uppercase text-sm leading-none">{proj.projectName}</h3>
                      <p className="text-[9px] uppercase mt-2 opacity-60 font-bold">{(proj.prospects || []).length} Targets Selected</p>
                    </button>
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
              <button onClick={() => { setActiveProject(null); setView('home'); }} className="mb-8 font-black uppercase text-xs border-2 border-black p-2 hover:bg-black hover:text-white transition-all">← GLOBAL TACTICAL BOARD</button>
              <h2 className="text-xl font-black uppercase mb-6 italic border-b-4 border-black pb-2 leading-tight">{activeProject.projectName}</h2>
              <div className="space-y-3 overflow-y-auto pr-2">
                {(() => {
                  const prospects = activeProject.prospects || [];
                  const maxRating = Math.max(0, ...prospects.map(p => (liveProspects[p.id] || p)._rating || 0));
                  
                  return prospects.map(p => {
                    const liveP = liveProspects[p.id] || p;
                    const isSelected = selectedProspect?.id === p.id;
                    
                    // Compare relative to the leader in the current list
                    const newR = liveP._rating || 0;
                    const dynDelta = maxRating > 0 ? Math.round(((newR - maxRating) / maxRating) * 100) : 0;
                    
                    const { text, textClass } = getDeltaStyling(dynDelta);
                    const statusShadow = dynDelta === 0 
                      ? 'shadow-[4px_4px_0px_0px_rgba(156,163,175,1)]' // Neutral gray for the top player
                      : 'shadow-[4px_4px_0px_0px_rgba(220,38,38,1)]';  // Red for lower prospects
                    
                    return (
                      <div 
                        key={p.id} 
                        onClick={() => setSelectedProspect(p)} 
                        className={`p-3 border-2 border-black cursor-pointer transition-all ${isSelected ? `bg-black text-white ${statusShadow} -translate-x-1 -translate-y-1` : 'bg-white hover:bg-gray-50'}`}
                      >
                        <div className="flex justify-between font-black text-[10px] uppercase italic mb-2">
                          <span className="truncate pr-2">{p.name}</span>
                          <span className={textClass}>
                            {text}
                          </span>
                        </div>
                      <div className="grid grid-cols-2 gap-2 text-[9px] font-bold">
                        <div className={`p-1 border border-current ${isSelected ? 'bg-white/10' : 'bg-gray-100'}`}>
                          <span className="opacity-60 block">RATING</span>
                          <span className="text-sm font-black">{newR}</span>
                        </div>
                        <div className={`p-1 border border-current ${isSelected ? 'bg-white/10' : 'bg-gray-100'}`}>
                          <span className="opacity-60 block">SYNERGY</span>
                          <span className="text-sm font-black">{liveP._synergy || 0}</span>
                        </div>
                      </div>
                    </div>
                  );
                  });
                })()}
              </div>
            </div>
          )}
        </aside>
      )}

      {/* --- 3. CENTER MAIN: THE SIMULATOR FIELD --- */}
      <main className="flex-1 p-10 flex flex-col items-center justify-start bg-[#fdfdfd]">
        <div className="w-full max-w-lg">
          <TacticalPitch 
            squad={squad.map(p => ({ ...p, deficit: getPlayerDeficit(p.roleId) }))} 
            shadowPlayer={view === 'project' && selectedProspect && activeProject?.replacedPlayer ? (() => {
              const liveP = liveProspects[selectedProspect.id] || selectedProspect;
              return { 
              ...liveP, 
              replaceId: activeProject.replacedPlayer.id, 
              position: activeProject.replacedPlayer.position, 
              value: liveP._rating ? Math.round(liveP._rating) : '-' 
              };
            })() : null} 
            showHeatmap={heatmap} 
            onPlayerClick={(p) => {
              if (heatmap) setHeatmap(false);
              view === 'edit_team' ? setEditTargetPlayer(p) : (view === 'home' && setTargetPlayer(p));
            }} 
          />
        </div>
      </main>

      {/* --- 4. RIGHT SIDEBAR: IN-DEPTH DATA PANEL --- */}
      {view === 'project' && selectedProspect && (() => {
        const liveData = liveProspects[selectedProspect.id] || selectedProspect;
        
        // Project Delta: Compare prospect's live stats vs their own baseline when project was created
        const baseRating = selectedProspect.initial_dynamic_rating || selectedProspect._rating || 0;
        const newRating = liveData._rating || 0;
        const ratingPct = baseRating > 0 ? Math.round(((newRating - baseRating) / baseRating) * 100) : 0;

        const baseSynergy = selectedProspect.initial_synergy_score || selectedProspect._synergy || 0;
        const newSynergy = liveData._synergy || 0;
        const synergyPct = baseSynergy > 0 ? Math.round(((newSynergy - baseSynergy) / baseSynergy) * 100) : 0;

        const reportText = liveData.reason || selectedProspect.reason;

        return (
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
            <div className={`p-4 border-2 border-black border-dashed relative transition-all duration-700 ${flashReport ? 'bg-yellow-300 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] -translate-y-1 -translate-x-1' : 'bg-gray-50'}`}>
              <div className="absolute -top-3 left-3 bg-black text-white text-[8px] px-2 font-black italic">INTELLIGENCE REPORT</div>
              <p className={`text-sm italic font-medium leading-relaxed ${!reportText ? 'text-gray-400' : 'text-black'}`}>
                {reportText ? `"${reportText}"` : 'No intelligence report available.'}
              </p>
            </div>

            {/* Fitting Rating */}
            <section>
              <div className="flex justify-between items-end mb-2">
                <div>
                  <span className="text-[10px] font-black uppercase tracking-widest italic underline decoration-2">Dynamic Rating</span>
                  <div className="text-[8px] uppercase font-bold text-gray-500 mt-1">Baseline: {baseRating}</div>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-3xl font-black leading-none">{newRating}</span>
                    <DeltaTag value={ratingPct} />
                </div>
              </div>
              <div className="h-6 border-4 border-black bg-white flex p-0.5 overflow-hidden">
                <div 
                  className="h-full bg-black transition-all duration-700" 
                    style={{ width: `${Math.min(baseRating, newRating)}%` }}
                ></div>
                  {newRating > baseRating && (
                    <div className="h-full bg-green-500 transition-all duration-1000" style={{ width: `${Math.min(newRating - baseRating, 100 - baseRating)}%` }}></div>
                  )}
                  {newRating < baseRating && (
                    <div className="h-full bg-red-600 transition-all duration-1000" style={{ width: `${baseRating - newRating}%` }}></div>
                  )}
              </div>
            </section>

            {/* Synergy Score */}
            <section>
              <div className="flex justify-between items-end mb-2">
                <div>
                  <span className="text-[10px] font-black uppercase tracking-widest italic underline decoration-2">Synergy Score</span>
                  <div className="text-[8px] uppercase font-bold text-gray-500 mt-1">Baseline: {baseSynergy}</div>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-3xl font-black leading-none">{newSynergy}</span>
                    <DeltaTag value={synergyPct} />
                </div>
              </div>
              <div className="h-6 border-4 border-black bg-white flex p-0.5 overflow-hidden">
                <div 
                  className="h-full bg-black transition-all duration-700" 
                    style={{ width: `${Math.min(baseSynergy, newSynergy)}%` }}
                ></div>
                  {newSynergy > baseSynergy && (
                    <div className="h-full bg-green-500 transition-all duration-1000" style={{ width: `${Math.min(newSynergy - baseSynergy, 100 - baseSynergy)}%` }}></div>
                  )}
                  {newSynergy < baseSynergy && (
                    <div className="h-full bg-red-600 transition-all duration-1000" style={{ width: `${baseSynergy - newSynergy}%` }}></div>
                  )}
              </div>
            </section>

              {/* Transfermarkt Scouting Grid */}
            <div className="pt-8 border-t-4 border-black">
                <h4 className="text-xs font-black uppercase mb-4 tracking-widest italic underline decoration-2 underline-offset-4">Scouting Details/90 minutes</h4>
              <div className="grid grid-cols-2 gap-4 max-h-80 overflow-y-auto pr-2 pb-4">
                {[
                  // 1. Dynamic stats sorted by position priority
                  ...sortStatsByPosition(liveData.key_stats_used, selectedProspect.position),
                  // 2. Hardcoded Transfermarkt stats anchored at the end
                  ['Market Value', selectedProspect.marketValue || 'N/A'],
                  ['Age', selectedProspect.age || '-'],
                  ['Foot', selectedProspect.foot || '-'],
                  ['Height', selectedProspect.height || '-']
                ].map(([key, val]) => (
                  <div key={key} className="border-2 border-black p-3 bg-gray-50 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:bg-black hover:text-white transition-colors group flex flex-col justify-between">
                    <p className="text-[8px] uppercase font-black opacity-40 mb-2 group-hover:opacity-100 leading-tight">{formatStatLabel(key)}</p>
                    <p className="text-xl font-black italic leading-none truncate" title={formatStatValue(val)}>{formatStatValue(val)}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
          </aside>
        );
      })()}

      {/* --- 5. RIGHT SIDEBAR: EDIT TEAM & PLAYER REPLACEMENTS --- */}
      {view === 'home' && (
        <aside className="w-80 border-l-4 border-black p-6 bg-white flex flex-col justify-start items-center relative z-10 shadow-2xl">
          <div className="absolute top-6 right-6 opacity-10 font-black italic text-5xl rotate-90 origin-top-right whitespace-nowrap">MANAGER MODE</div>
          <div className="z-10 text-center w-full">
            <h3 className="font-black text-2xl uppercase italic tracking-tighter mb-4">Tactical Board</h3>
            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-8 border-b-2 border-black pb-4">Adjust Starting XI & Formation</p>
            <button 
              onClick={() => {
                setBackupSquad([...squad]);
                setView('edit_team');
                setEditTargetPlayer(null);
              }} 
              className="w-full p-4 bg-black text-white font-black uppercase italic border-4 border-black hover:bg-white hover:text-black hover:-translate-y-1 hover:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] transition-all"
            >
              Modify Your Team
            </button>
          </div>
        </aside>
      )}

      {view === 'edit_team' && (
        <aside className="w-96 border-l-4 border-black bg-white flex flex-col z-10 shadow-2xl">
          {!editTargetPlayer ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center opacity-40">
              <div className="text-4xl mb-4">👆</div>
              <p className="font-black uppercase tracking-widest">Select a player on the pitch to view replacements</p>
            </div>
          ) : (
            <div className="p-6 flex flex-col h-full">
              <div className="mb-6 pb-6 border-b-4 border-black">
                <h3 className="text-2xl font-black uppercase italic tracking-tighter leading-none mb-1">{editTargetPlayer.name}</h3>
                <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Current Starter • {editTargetPlayer.roleId}</p>
              </div>

              <h4 className="text-[10px] font-black uppercase tracking-widest mb-4 italic decoration-2 underline">Available Substitutes</h4>
              
              <div className="flex-1 overflow-y-auto space-y-3 pr-2">
                {(() => {
                  const activeIds = squad.map(p => p.id);
                  const keywords = getRoleKeywords(editTargetPlayer.roleId.toUpperCase());
                  
                  const replacements = allTeamPlayers.filter(p => 
                    !activeIds.includes(p.player_id) && 
                    keywords.some(kw => p.position && p.position.toUpperCase().includes(kw))
                  );

                  if (replacements.length === 0) {
                    return <p className="text-xs font-bold text-gray-400 italic">No available substitutes for this exact role.</p>;
                  }

                  return replacements.map(r => (
                    <div 
                      key={r.player_id} 
                      onClick={() => handleSwapPlayer(r)}
                      className="p-3 border-2 border-black cursor-pointer bg-white hover:bg-black hover:text-white transition-colors group flex justify-between items-center"
                    >
                      <div>
                        <p className="text-xs font-black uppercase">{r.name}</p>
                        <p className="text-[9px] font-bold opacity-60">Mins: {r.key_stats_used?.['Minutes Played'] || 0}</p>
                      </div>
                      <div className="text-right">
                        <span className="block text-lg font-black leading-none">{r.base_bpi ? Math.round(r.base_bpi) : '-'}</span>
                        <span className="text-[7px] uppercase font-bold tracking-widest opacity-50">BPI</span>
                      </div>
                    </div>
                  ));
                })()}
              </div>
            </div>
          )}
        </aside>
      )}
    </div>
  );
}