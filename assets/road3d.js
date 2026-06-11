// The Year Road — a winding low-poly timeline through stylized terrain.
// Light-weight (<50 draw calls): one road mesh, one terrain, sky, fog, ~15 markers.
import * as THREE from "three";

const DT_COLOR = {
  content:0x4d9dff, quiz:0xffc34d, test:0xff5a6e, crq:0xc98bff, eie:0xff4d9d,
  mock:0xff8a3d, project:0x3ddc84, review:0x28e0d4, exam:0xff2e5b,
  launch:0x8b7dff, closeout:0x8ea0c4,
};

export function initRoad(days, onJump) {
  const canvas = document.getElementById("road3d");
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x070b18);
  scene.fog = new THREE.Fog(0x070b18, 18, 95);

  const camera = new THREE.PerspectiveCamera(55, 2, 0.1, 400);
  const renderer = new THREE.WebGLRenderer({ canvas, antialias:true });
  renderer.setPixelRatio(Math.min(devicePixelRatio,2));

  // lights
  scene.add(new THREE.HemisphereLight(0x9fb8ff, 0x0a0f1e, 0.9));
  const sun = new THREE.DirectionalLight(0xffe6b0, 0.8);
  sun.position.set(-30, 40, 20); scene.add(sun);

  // --- build the road path (a gentle winding curve along +Z) ---
  const N = days.length;
  const pts = [];
  for (let i=0;i<N;i++){
    const t=i/(N-1);
    const z = -t*220;                       // forward
    const x = Math.sin(t*Math.PI*4)*14 + Math.sin(t*Math.PI*1.3)*6; // winding
    const y = Math.sin(t*Math.PI*2.2)*1.4;  // gentle hills
    pts.push(new THREE.Vector3(x,y,z));
  }
  const curve = new THREE.CatmullRomCurve3(pts);

  // terrain (low-poly plane with vertex colors)
  const geo = new THREE.PlaneGeometry(260, 300, 60, 70);
  geo.rotateX(-Math.PI/2);
  const pos = geo.attributes.position;
  const colors = [];
  const cLow = new THREE.Color(0x0c1830), cHi = new THREE.Color(0x16344a), cTop=new THREE.Color(0x1f5a55);
  for (let i=0;i<pos.count;i++){
    const px=pos.getX(i), pz=pos.getZ(i);
    // keep a valley along the road corridor (x near the winding curve)
    const corridorX = Math.sin((-pz/220)*Math.PI*4)*14 + Math.sin((-pz/220)*Math.PI*1.3)*6;
    const dist = Math.abs(px-corridorX);
    let h = (Math.sin(px*0.12)*Math.cos(pz*0.1)+Math.sin(px*0.05+pz*0.07))*2.4;
    h += Math.max(0, dist-10)*0.22;          // hills rise away from road
    if (dist<7) h = Math.min(h, 0.3);         // flatten corridor
    pos.setY(i, h-2.2);
    const c = h>5? cTop : (h>1.6? cHi : cLow);
    colors.push(c.r,c.g,c.b);
  }
  geo.setAttribute("color", new THREE.Float32BufferAttribute(colors,3));
  geo.computeVertexNormals();
  const terrain = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({vertexColors:true, flatShading:true, roughness:1}));
  terrain.position.z=-110; scene.add(terrain);

  // road ribbon
  const roadGeo = new THREE.TubeGeometry(curve, 240, 1.7, 8, false);
  const road = new THREE.Mesh(roadGeo, new THREE.MeshStandardMaterial({color:0x1a2740, roughness:.85, metalness:.1, flatShading:true}));
  scene.add(road);
  // glowing centerline
  const lineGeo = new THREE.TubeGeometry(curve, 240, 0.12, 5, false);
  scene.add(new THREE.Mesh(lineGeo, new THREE.MeshBasicMaterial({color:0x28e0d4})));

  // sky dome (gradient via large back-faced sphere)
  const sky = new THREE.Mesh(
    new THREE.SphereGeometry(200, 24, 16),
    new THREE.ShaderMaterial({ side:THREE.BackSide, uniforms:{}, vertexShader:`
      varying vec3 vp; void main(){vp=position; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
      fragmentShader:`varying vec3 vp; void main(){ float t=clamp((normalize(vp).y+0.2)*0.9,0.,1.);
        vec3 top=vec3(0.027,0.043,0.094), mid=vec3(0.06,0.10,0.22), bot=vec3(0.10,0.13,0.20);
        vec3 c = t>0.5? mix(mid,top,(t-0.5)*2.) : mix(bot,mid,t*2.);
        gl_FragColor=vec4(c,1.);}` }));
  scene.add(sky);

  // stars (points)
  const sg=new THREE.BufferGeometry(); const sp=[];
  for(let i=0;i<260;i++){const r=160,th=Math.random()*Math.PI*2,ph=Math.random()*Math.PI*0.4+0.1;
    sp.push(Math.cos(th)*Math.sin(ph)*r, Math.cos(ph)*r*0.8, Math.sin(th)*Math.sin(ph)*r);}
  sg.setAttribute("position", new THREE.Float32BufferAttribute(sp,3));
  scene.add(new THREE.Points(sg, new THREE.PointsMaterial({color:0x8ea0c4, size:0.7})));

  // --- markers: unit-gate landmarks + key events ---
  const markers = [];           // {mesh, idx, label}
  const raycaster = new THREE.Raycaster();
  const mouse = new THREE.Vector2();

  // pick landmark days: first day of each G9R unit + any key_event day
  const seenUnit = new Set();
  const landmarkIdx = new Set();
  days.forEach((d,i)=>{
    const u = d.global9.unit;
    if (u && !seenUnit.has(u)) { seenUnit.add(u); landmarkIdx.add(i); }
    if (d.key_event) landmarkIdx.add(i);
  });

  function tubePoint(i){ return curve.getPointAt(Math.min(0.999, i/(N-1))); }

  landmarkIdx.forEach(i=>{
    const d = days[i];
    const p = tubePoint(i);
    const isEvent = !!d.key_event;
    const col = isEvent ? 0xff4d9d : (DT_COLOR[d.global9.day_type]||0x28e0d4);
    // post
    const post = new THREE.Mesh(new THREE.CylinderGeometry(0.12,0.12,isEvent?4:3,6),
      new THREE.MeshStandardMaterial({color:0x33415f, flatShading:true}));
    post.position.set(p.x, p.y+(isEvent?2:1.5), p.z); scene.add(post);
    // gem
    const gem = new THREE.Mesh(new THREE.OctahedronGeometry(isEvent?1.1:0.8),
      new THREE.MeshStandardMaterial({color:col, emissive:col, emissiveIntensity:.55, flatShading:true}));
    gem.position.set(p.x, p.y+(isEvent?4:3), p.z);
    gem.userData = {idx:i, base:gem.position.y};
    scene.add(gem);
    // glow halo
    const halo = new THREE.Mesh(new THREE.SphereGeometry(isEvent?1.7:1.2,10,10),
      new THREE.MeshBasicMaterial({color:col, transparent:true, opacity:.12}));
    halo.position.copy(gem.position); scene.add(halo);
    markers.push({mesh:gem, halo, idx:i, label:(d.key_event||d.global9.unit||"")});
  });

  // legend (day-types present)
  const legendEl = document.getElementById("heroLegend");
  if (legendEl){
    const items = [["unit","Unit gate",0x28e0d4],["event","Key event",0xff4d9d],
      ["test","Test",0xff5a6e],["mock","Mock",0xff8a3d],["exam","Exam",0xff2e5b]];
    legendEl.innerHTML = items.map(([k,l,c])=>
      `<span class="lg"><span class="dot" style="background:#${c.toString(16).padStart(6,'0')}"></span>${l}</span>`).join("");
  }

  // --- camera follows a target index along the road ---
  let camIdx = 0, targetIdx = 0;
  function setCam(i, snap=false){
    targetIdx = Math.max(0, Math.min(N-1, i));
    if (snap) camIdx = targetIdx;
  }
  function updateCam(){
    camIdx += (targetIdx - camIdx)*0.08;
    const f = Math.min(0.999, camIdx/(N-1));
    const here = curve.getPointAt(f);
    const ahead = curve.getPointAt(Math.min(0.999, f+0.02));
    camera.position.set(here.x - 6, here.y + 6.5, here.z + 12);
    camera.lookAt(ahead.x, ahead.y+1.2, ahead.z - 4);
  }

  // interaction: click a marker -> jump
  canvas.addEventListener("pointerdown", e=>{
    const r = canvas.getBoundingClientRect();
    mouse.x = ((e.clientX-r.left)/r.width)*2-1;
    mouse.y = -((e.clientY-r.top)/r.height)*2+1;
    raycaster.setFromCamera(mouse, camera);
    const hits = raycaster.intersectObjects(markers.map(m=>m.mesh));
    if (hits.length){ const idx=hits[0].object.userData.idx; onJump(idx); }
  });

  function resize(){
    const w=canvas.clientWidth, h=canvas.clientHeight;
    if (canvas.width!==w||canvas.height!==h){ renderer.setSize(w,h,false); camera.aspect=w/h; camera.updateProjectionMatrix(); }
  }
  let t=0;
  function loop(){
    requestAnimationFrame(loop);
    resize(); updateCam(); t+=0.016;
    markers.forEach((m,k)=>{ m.mesh.rotation.y=t*0.8+k; m.mesh.position.y=m.mesh.userData.base+Math.sin(t*1.5+k)*0.18;
      m.halo.position.y=m.mesh.position.y; });
    renderer.render(scene,camera);
  }
  loop();

  return { setCam, markerCount: markers.length, drawInfo:`markers=${markers.length}` };
}
