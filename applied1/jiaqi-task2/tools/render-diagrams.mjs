import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const sharp = require('/Users/liujiaqi/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const out = path.join(root, 'figures');
fs.mkdirSync(out, { recursive: true });

const C = {
  ink: '#0f172a', muted: '#475569', blue: '#2563eb', blue2: '#dbeafe',
  teal: '#0f766e', teal2: '#ccfbf1', amber: '#d97706', amber2: '#fef3c7',
  violet: '#7c3aed', violet2: '#ede9fe', line: '#cbd5e1', soft: '#f8fafc', white: '#ffffff'
};

const esc = s => String(s).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
const text = (x, y, value, size=24, weight=400, fill=C.ink, anchor='start') =>
  `<text x="${x}" y="${y}" font-family="Arial, Helvetica, sans-serif" font-size="${size}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}">${esc(value)}</text>`;
const line = (x1,y1,x2,y2,stroke=C.line,width=3,dash='') =>
  `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${stroke}" stroke-width="${width}" ${dash ? `stroke-dasharray="${dash}"` : ''}/>`;
const arrow = (x1,y1,x2,y2,label,color=C.blue,dash='') => {
  const back = x2 >= x1 ? x2-14 : x2+14;
  return `${line(x1,y1,x2,y2,color,3,dash)}<polygon points="${x2},${y2} ${back},${y2-8} ${back},${y2+8}" fill="${color}"/>${text((x1+x2)/2,y1-11,label,19,600,C.ink,'middle')}`;
};

function svgWrap(w,h,body,title){
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(title)}">
<rect width="${w}" height="${h}" fill="${C.white}"/>
${body}
</svg>`;
}

function classBox(x,y,w,h,titleName,fields,methods,color,light){
  const head=62, split=y+head+fields.length*28+18;
  let s=`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="14" fill="${C.white}" stroke="${color}" stroke-width="3"/>`;
  s+=`<path d="M ${x+14} ${y} H ${x+w-14} Q ${x+w} ${y} ${x+w} ${y+14} V ${y+head} H ${x} V ${y+14} Q ${x} ${y} ${x+14} ${y}" fill="${light}"/>`;
  s+=text(x+w/2,y+40,titleName,25,700,C.ink,'middle');
  fields.forEach((f,i)=>s+=text(x+20,y+92+i*28,f,18,400,C.muted));
  s+=line(x,split,x+w,split,C.line,2);
  methods.forEach((m,i)=>s+=text(x+20,split+34+i*28,m,18,600,color));
  return s;
}

function classDiagram(){
  let b=text(70,65,'Task 2 · Static software structure',38,700)+text(70,102,'MPI processes model stations; ports remain local objects.',21,400,C.muted);
  b+=classBox(70,145,400,260,'SimulationConfig',['R, C, S, P','threshold, rounds, frequency'],['validate()','broadcastConfig()'],C.violet,C.violet2);
  b+=classBox(600,145,400,260,'Topology',['mesh dimensions','region ownership'],['createCartesianMesh()','getAssignedBase()'],C.teal,C.teal2);
  b+=classBox(1130,145,400,260,'DistancePolicy',['logical coordinates','tie-break: smaller nodeId'],['manhattanDistance()','compareCandidate()'],C.amber,C.amber2);
  b+=classBox(100,530,500,360,'ChargingNode',['nodeId, coordinate','ports[P], utilisation','neighbourRanks','assignedBaseRank'],['updatePorts()','queryNeighbours()','sendStatus()','sendAlertDecision()'],C.blue,C.blue2);
  b+=classBox(1000,530,500,360,'BaseStation',['baseId, region','statusCache, eventLog','candidateVector'],['receiveReports()','allgatherAlertCounts()','allgathervAlertBatches()','findRegionalCandidates()','allreduceWinners()','sendRedirect()'],C.teal,C.teal2);
  b+=classBox(655,625,290,205,'ChargingPort',['portId','FREE / BUSY'],['setStatus()'],C.violet,C.violet2);
  b+=arrow(470,270,600,270,'configures',C.violet);
  b+=arrow(1000,270,1130,270,'uses policy',C.amber);
  b+=arrow(800,405,420,530,'defines neighbours',C.teal);
  b+=arrow(830,405,1210,530,'defines regions',C.teal);
  b+=arrow(600,540,655,625,'contains 1..*',C.blue);
  b+=arrow(1000,590,600,590,'manages 1..*',C.teal);
  b+=arrow(1130,405,1250,530,'selects candidates',C.amber);
  return svgWrap(1600,980,b,'Task 2 static class diagram');
}

function sequenceDiagram(){
  const xs=[170,540,980,1430], names=['Charging node','Logical neighbours','Assigned base','base_comm (all bases)'];
  let b=text(70,58,'Task 2 · Communication sequence for one round',38,700)+text(70,94,'Fixed completion rules for nodes; one ordered collective batch for bases.',21,400,C.muted);
  xs.forEach((x,i)=>{b+=`<rect x="${x-125}" y="125" width="250" height="58" rx="12" fill="${i===3?C.violet2:C.blue2}" stroke="${i===3?C.violet:C.blue}" stroke-width="2"/>`;b+=text(x,162,names[i],20,700,C.ink,'middle');b+=line(x,183,x,1115,C.line,2,'8 8');});
  const band=(y,h,label,fill)=>{b+=`<rect x="55" y="${y}" width="1490" height="${h}" rx="10" fill="${fill}" opacity="0.55"/>`;b+=text(75,y+28,label,17,700,C.muted);};
  band(205,150,'1 · Regional status',C.blue2);
  b+=arrow(xs[0],265,xs[2],265,'STATUS_REPORT · Isend/Irecv',C.blue);
  b+=text(xs[2]+18,315,'Waitall → cache + log + heavy set H_s',18,600,C.teal);
  band(365,210,'2 · Logical neighbour sensing',C.teal2);
  b+=arrow(xs[0],425,xs[1],425,'QUERY(active flag)',C.teal);
  b+=arrow(xs[1],485,xs[0],485,'QUERY(active flag)',C.teal);
  b+=arrow(xs[1],545,xs[0],545,'NEIGHBOUR_REPLY if active',C.teal);
  band(585,120,'3 · Finite alert decision',C.amber2);
  b+=arrow(xs[0],650,xs[2],650,'ALERT_DECISION(true / false)',C.amber);
  band(715,245,'4 · Ordered base collective phase',C.violet2);
  b+=text(1310,727,'all S bases participate',16,700,C.violet,'middle');
  b+=arrow(xs[2],770,xs[3],770,'Allgather(local alert counts)',C.violet);
  b+=arrow(xs[2],825,xs[3],825,'Allgatherv(alert batches)',C.violet);
  b+=text(xs[2],875,'OpenMP regional search',18,700,C.teal,'middle');
  b+=arrow(xs[2],925,xs[3],925,'Vector Allreduce(MINLOC)',C.violet);
  band(970,145,'5 · Result and round completion',C.blue2);
  b+=arrow(xs[2],1025,xs[0],1025,'REDIRECT · Send/Recv',C.blue);
  b+=arrow(xs[0],1080,xs[3],1080,'MPI_Barrier(MPI_COMM_WORLD)',C.muted,'8 6');
  return svgWrap(1600,1180,b,'Task 2 communication sequence diagram');
}

function commDeployment(){
  let b=text(70,58,'Task 2 · Communicators and cluster deployment',38,700)+text(70,94,'Logical MPI groups above; locality-aware four-host mapping below.',21,400,C.muted);
  const box=(x,y,w,h,label,sub,color,light)=>`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="14" fill="${light}" stroke="${color}" stroke-width="3"/>${text(x+w/2,y+38,label,23,700,C.ink,'middle')}${text(x+w/2,y+70,sub,17,400,C.muted,'middle')}`;
  b+=box(575,130,450,90,'MPI_COMM_WORLD','N + S ranks',C.blue,C.blue2);
  b+=line(800,220,800,265,C.blue,3);b+=line(385,265,1215,265,C.blue,3);b+=line(385,265,385,300,C.blue,3);b+=line(1215,265,1215,300,C.blue,3);
  b+=box(175,300,420,95,'base_comm','S base stations · collectives',C.violet,C.violet2);
  b+=box(1005,300,420,95,'node_comm','N charging nodes · setup only',C.teal,C.teal2);
  b+=line(1215,395,1215,445,C.teal,3);
  b+=box(1005,445,420,95,'cart_comm','R × C non-periodic mesh',C.teal,C.teal2);
  b+=text(385,430,'Allgather counts',18,600,C.violet,'middle');b+=text(385,458,'Allgatherv alerts',18,600,C.violet,'middle');b+=text(385,486,'Allreduce MINLOC',18,600,C.violet,'middle');
  b+=text(1215,575,'QUERY · NEIGHBOUR_REPLY',18,600,C.teal,'middle');
  b+=line(70,625,1530,625,C.line,2);
  b+=text(70,670,'Selected physical mapping · four 32-core hosts',27,700,C.ink);
  const hostXs=[70,455,840,1225];
  hostXs.forEach((x,i)=>{b+=`<rect x="${x}" y="710" width="305" height="210" rx="16" fill="${C.soft}" stroke="${C.line}" stroke-width="3"/>`;b+=text(x+22,750,`Host ${i} · Region ${i}`,22,700,C.ink);b+=`<rect x="${x+22}" y="780" width="110" height="54" rx="10" fill="${C.violet2}" stroke="${C.violet}" stroke-width="2"/>`;b+=text(x+77,813,`Base ${i}`,18,700,C.violet,'middle');b+=text(x+160,800,'16 node ranks',18,600,C.blue);b+=text(x+160,828,'4 OpenMP threads',18,600,C.teal);b+=text(x+22,875,'20 active / 32 cores',19,700,C.ink);});
  for(let i=0;i<3;i++) b+=line(hostXs[i]+305,900,hostXs[i+1],900,C.amber,4,'10 7');
  b+=`<rect x="70" y="955" width="1460" height="100" rx="14" fill="${C.amber2}" stroke="${C.amber}" stroke-width="2"/>`;
  b+=text(105,995,'80 active cores',21,700,C.ink);b+=text(390,995,'3 hosts minimum',21,700,C.ink);b+=text(700,995,'4 hosts selected for locality',21,700,C.ink);b+=text(1160,995,'0.15664 Mbps @ 1 round/s',21,700,C.ink);
  b+=text(105,1030,'WORLD: CONFIG / STATUS / ALERT / REDIRECT / BARRIER',17,600,C.muted);
  return svgWrap(1600,1100,b,'Task 2 communicator and deployment diagram');
}

const diagrams = [
  ['task2-class-diagram', classDiagram()],
  ['task2-sequence-diagram', sequenceDiagram()],
  ['task2-communicators-deployment', commDeployment()]
];

for (const [name, svg] of diagrams) {
  const svgPath = path.join(out, `${name}.svg`);
  const pngPath = path.join(out, `${name}.png`);
  fs.writeFileSync(svgPath, svg);
  await sharp(Buffer.from(svg)).png().toFile(pngPath);
}

console.log(`Rendered ${diagrams.length} diagrams to ${out}`);
