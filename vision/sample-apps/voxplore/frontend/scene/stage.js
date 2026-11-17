/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

// Runtime shared by every generated scene: canvas, camera, controls, picking, sliders and the link
// to the tutor. A scene only describes what is specific to it.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

const tutor = window.tutor || { event() {} };

// The controls sit beside the view (or under it in a narrow window), never on top of it
const style = document.createElement('style');
style.textContent = `
html, body { margin: 0; height: 100%; overflow: hidden; background: #141b24; color: #e9eef3; font: 14px/1.4 system-ui, sans-serif; }
body { display: flex; flex-direction: row; }
canvas { display: block; }
#stage-view { position: relative; flex: 1; min-width: 0; min-height: 0; overflow: hidden; }
#stage-panel { display: none; flex-direction: column; gap: 10px; width: 200px; flex-shrink: 0; box-sizing: border-box; padding: 12px; overflow-y: auto; background: rgba(20, 27, 36, 0.9); border-right: 1px solid rgba(255, 255, 255, 0.12); }
#stage-panel > * { min-width: 0; }
#stage-panel label { display: flex; justify-content: space-between; gap: 8px; font-size: 12px; color: #c3ced9; }
#stage-panel b { color: #e9eef3; font-weight: 600; font-variant-numeric: tabular-nums; }
#stage-panel input[type=range] { width: 100%; margin: 2px 0 0; accent-color: #7dbcff; }
#stage-panel button { padding: 6px 10px; border-radius: 6px; border: 1px solid rgba(125, 188, 255, 0.5); background: rgba(90, 169, 255, 0.25); color: #e6f1ff; font: inherit; cursor: pointer; }
#stage-panel button:hover { background: rgba(90, 169, 255, 0.45); }
@media (max-width: 640px) {
    body { flex-direction: column-reverse; }
    #stage-panel { flex-direction: row; flex-wrap: wrap; align-items: center; width: auto; max-height: 40%; gap: 8px 14px; padding: 8px 12px; border-right: 0; border-top: 1px solid rgba(255, 255, 255, 0.12); }
    #stage-panel > * { flex: 1 1 130px; }
    #stage-panel > button { flex: 0 1 auto; }
}
#stage-info { position: absolute; left: 50%; bottom: 12px; transform: translateX(-50%); max-width: 80%; display: none; padding: 8px 14px; border-radius: 10px; background: rgba(20, 27, 36, 0.88); border: 1px solid rgba(125, 188, 255, 0.45); text-align: center; z-index: 5; }
#stage-info b { display: block; }
#stage-info span { font-size: 12px; color: #c3ced9; }
#stage-caption { position: absolute; top: 10px; right: 12px; max-width: 60%; font-size: 12px; color: #9aa8b8; text-align: right; z-index: 5; pointer-events: none; }
.stage-label { margin-top: -1.8em; padding: 1px 6px; border-radius: 4px; background: rgba(20, 27, 36, 0.7); color: #e9eef3; font-size: 12px; white-space: nowrap; pointer-events: none; }
`;
document.head.appendChild(style);

function el(tag, props, parent) {
    const node = Object.assign(document.createElement(tag), props || {});
    (parent || document.body).appendChild(node);
    return node;
}

const panel = el('div', { id: 'stage-panel' });
const viewBox = el('div', { id: 'stage-view' });
const infoBox = el('div', { id: 'stage-info' }, viewBox);
const captionBox = el('div', { id: 'stage-caption' }, viewBox);

const frameCallbacks = [];
const renderers = [];
const reported = new Set();
const counts = { mode: null, parts: 0, sliders: 0, buttons: 0 };
let selectedName = null;
let failed = false;

function fail(error) {
    if (failed) return;
    failed = true;
    parent.postMessage({ scene: true, type: 'error', message: String((error && error.message) || error) }, '*');
}

function guarded(fn) {
    return (...args) => {
        try {
            return fn(...args);
        } catch (error) {
            fail(error);
        }
    };
}

function viewSize() {
    return [Math.max(viewBox.clientWidth, 1), Math.max(viewBox.clientHeight, 1)];
}

// The view changes size with the window and when the control panel appears
function onViewResize(fn) {
    new ResizeObserver(fn).observe(viewBox);
    fn();
}

function slider(name, min, max, value, step, onInput) {
    panel.style.display = 'flex';
    counts.sliders++;
    const row = el('div', {}, panel);
    const label = el('label', {}, row);
    el('span', { textContent: name }, label);
    const shown = el('b', {}, label);
    const input = el('input', { type: 'range', min, max, step: step || (max - min) / 100 }, row);
    input.value = value;
    let current = Number(value);
    const format = (v) => String(Math.round(v * 1000) / 1000);
    shown.textContent = format(current);
    input.addEventListener('input', guarded(() => {
        current = Number(input.value);
        shown.textContent = format(current);
        if (onInput) onInput(current);
    }));
    input.addEventListener('change', () => tutor.event('set', { name, value: current }));
    return () => current;
}

function button(label, onClick) {
    panel.style.display = 'flex';
    counts.buttons++;
    const node = el('button', { textContent: label }, panel);
    node.addEventListener('click', guarded(() => {
        tutor.event('press', { button: label });
        if (onClick) onClick();
    }));
    return node;
}

function readout(name) {
    panel.style.display = 'flex';
    const label = el('label', {}, panel);
    el('span', { textContent: name }, label);
    const shown = el('b', {}, label);
    return (value) => {
        shown.textContent = typeof value === 'number' ? String(Math.round(value * 1000) / 1000) : String(value);
    };
}

function caption(text) {
    captionBox.textContent = text;
}

function info(title, text) {
    infoBox.innerHTML = '';
    el('b', { textContent: title }, infoBox);
    if (text) el('span', { textContent: text }, infoBox);
    infoBox.style.display = 'block';
}

function select(name, description) {
    selectedName = name;
    info(name, description);
    tutor.event('select', { part: name });
}

// Something notable happened in a simulation; reported to the tutor once per distinct text
function outcome(what) {
    if (reported.has(what)) return;
    reported.add(what);
    tutor.event('outcome', { what });
}

function onFrame(fn) {
    frameCallbacks.push(fn);
}

const startedAt = performance.now();
let lastFrame = startedAt;
function tick(now) {
    const t = (now - startedAt) / 1000;
    const dt = Math.min((now - lastFrame) / 1000, 0.05);
    lastFrame = now;
    if (!failed) {
        try {
            for (const fn of frameCallbacks) fn(t, dt);
        } catch (error) {
            fail(error);
        }
    }
    try {
        for (const render of renderers) render(t, dt);
    } catch (error) {
        fail(error);
    }
    requestAnimationFrame(tick);
}
requestAnimationFrame(tick);

function vec(p) {
    if (Array.isArray(p)) return new THREE.Vector3(p[0], p[1], p[2] || 0);
    if (p && p.isObject3D) return p.position.clone();
    return p.clone();
}

function three(options = {}) {
    counts.mode = '3d';
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    viewBox.appendChild(renderer.domElement);
    const labels = new CSS2DRenderer();
    Object.assign(labels.domElement.style, { position: 'absolute', top: '0', left: '0', pointerEvents: 'none' });
    viewBox.appendChild(labels.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(options.background ?? 0x141b24);
    const camera = new THREE.PerspectiveCamera(50, 1, 0.05, 2000);
    camera.position.copy(vec(options.camera || [4, 3, 6]));
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.target.copy(vec(options.target || [0, 0, 0]));
    scene.add(new THREE.HemisphereLight(0xffffff, 0x334155, 1.1));
    const sun = new THREE.DirectionalLight(0xffffff, 1.6);
    sun.position.set(5, 8, 6);
    scene.add(sun);

    onViewResize(() => {
        const [w, h] = viewSize();
        renderer.setSize(w, h);
        labels.setSize(w, h);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
    });
    renderers.push(() => {
        controls.update();
        renderer.render(scene, camera);
        labels.render(scene, camera);
    });

    const parts = [];
    let glowing = null;
    function glow(object, on) {
        object.traverse((node) => {
            const material = node.material;
            if (!material || !material.emissive) return;
            if (on) {
                node.userData.stageEmissive = [material.emissive.getHex(), material.emissiveIntensity];
                material.emissive.setHex(0x4d8fe0);
                material.emissiveIntensity = 0.55;
            } else if (node.userData.stageEmissive) {
                material.emissive.setHex(node.userData.stageEmissive[0]);
                material.emissiveIntensity = node.userData.stageEmissive[1];
            }
        });
    }
    function pick(part) {
        if (glowing) glow(glowing.object, false);
        glowing = part;
        glow(part.object, true);
        select(part.name, part.description);
    }

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    let down = null;
    renderer.domElement.addEventListener('pointerdown', (e) => {
        down = [e.clientX, e.clientY];
    });
    renderer.domElement.addEventListener('pointerup', (e) => {
        // a drag rotates the view; only a still click selects
        if (!down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 5) return;
        const box = renderer.domElement.getBoundingClientRect();
        pointer.set(((e.clientX - box.left) / box.width) * 2 - 1, -((e.clientY - box.top) / box.height) * 2 + 1);
        raycaster.setFromCamera(pointer, camera);
        const hit = raycaster.intersectObjects(parts.map((p) => p.object), true)[0];
        let node = hit && hit.object;
        while (node) {
            const part = parts.find((p) => p.object === node);
            if (part) {
                pick(part);
                return;
            }
            node = node.parent;
        }
    });

    function part(object, name, description) {
        // own material per part, so highlighting one does not light up its twins
        object.traverse((node) => {
            if (node.isMesh && node.material && !Array.isArray(node.material)) node.material = node.material.clone();
        });
        object.userData.name = name;
        parts.push({ object, name, description });
        counts.parts++;
        return object;
    }

    function sphere(radius, color, position) {
        const mesh = new THREE.Mesh(new THREE.SphereGeometry(radius, 40, 24),
            new THREE.MeshStandardMaterial({ color, roughness: 0.45 }));
        if (position) mesh.position.copy(vec(position));
        scene.add(mesh);
        return mesh;
    }

    function bond(a, b, radius = 0.07, color = 0xbfc7d5) {
        const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, 1, 20),
            new THREE.MeshStandardMaterial({ color, roughness: 0.5 }));
        mesh.setEnds = (from, to) => {
            const start = vec(from);
            const end = vec(to);
            mesh.scale.y = Math.max(start.distanceTo(end), 1e-6);
            mesh.position.copy(start).add(end).multiplyScalar(0.5);
            mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), end.sub(start).normalize());
        };
        mesh.setEnds(a, b);
        scene.add(mesh);
        return mesh;
    }

    function line(points, color = 0x94a3b8) {
        const object = new THREE.Line(new THREE.BufferGeometry().setFromPoints(points.map(vec)),
            new THREE.LineBasicMaterial({ color }));
        scene.add(object);
        return object;
    }

    function label(target, text) {
        const tag = new CSS2DObject(Object.assign(document.createElement('div'), { className: 'stage-label', textContent: text }));
        if (target && target.isObject3D) {
            target.add(tag);
        } else {
            tag.position.copy(vec(target));
            scene.add(tag);
        }
        return tag;
    }

    return { scene, camera, controls, renderer, part, sphere, bond, line, label };
}

function niceStep(span) {
    const rough = span / 7;
    const power = Math.pow(10, Math.floor(Math.log10(rough)));
    for (const factor of [1, 2, 5, 10]) {
        if (factor * power >= rough) return factor * power;
    }
    return 10 * power;
}

function plot(options = {}) {
    counts.mode = '2d';
    const canvas = el('canvas', {}, viewBox);
    const ctx = canvas.getContext('2d');
    let xRange = options.x || [-5, 5];
    let yRange = options.y || [-5, 5];
    const showAxes = options.axes !== false;
    const margin = showAxes ? 46 : 16;
    const drawers = [];
    let dragHandler = null;
    let hits = [];
    let view = null;

    function layout() {
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        const [w, h] = viewSize();
        canvas.width = w * dpr;
        canvas.height = h * dpr;
        canvas.style.width = `${w}px`;
        canvas.style.height = `${h}px`;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        let sx = Math.max(w - 2 * margin, 10) / (xRange[1] - xRange[0]);
        let sy = Math.max(h - 2 * margin, 10) / (yRange[1] - yRange[0]);
        if (options.equal) sx = sy = Math.min(sx, sy);
        const cx = (xRange[0] + xRange[1]) / 2;
        const cy = (yRange[0] + yRange[1]) / 2;
        view = {
            w, h, sx, sy,
            px: (x) => w / 2 + (x - cx) * sx,
            py: (y) => h / 2 - (y - cy) * sy,
            wx: (p) => cx + (p - w / 2) / sx,
            wy: (p) => cy - (p - h / 2) / sy,
        };
    }
    onViewResize(layout);

    function drawAxes() {
        const left = view.wx(margin);
        const right = view.wx(view.w - margin);
        const bottom = view.wy(view.h - margin);
        const top = view.wy(margin);
        ctx.font = '11px system-ui, sans-serif';
        ctx.lineWidth = 1;
        const stepX = niceStep(right - left);
        const stepY = niceStep(top - bottom);
        const axisY = view.py(Math.min(Math.max(0, bottom), top));
        const axisX = view.px(Math.min(Math.max(0, left), right));
        ctx.fillStyle = '#9aa8b8';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        for (let x = Math.ceil(left / stepX) * stepX; x <= right + 1e-9; x += stepX) {
            ctx.strokeStyle = 'rgba(154, 168, 184, 0.13)';
            ctx.beginPath();
            ctx.moveTo(view.px(x), margin);
            ctx.lineTo(view.px(x), view.h - margin);
            ctx.stroke();
            if (Math.abs(x) > stepX / 2) ctx.fillText(String(Math.round(x * 1000) / 1000), view.px(x), axisY + 4);
        }
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        for (let y = Math.ceil(bottom / stepY) * stepY; y <= top + 1e-9; y += stepY) {
            ctx.strokeStyle = 'rgba(154, 168, 184, 0.13)';
            ctx.beginPath();
            ctx.moveTo(margin, view.py(y));
            ctx.lineTo(view.w - margin, view.py(y));
            ctx.stroke();
            if (Math.abs(y) > stepY / 2) ctx.fillText(String(Math.round(y * 1000) / 1000), axisX - 5, view.py(y));
        }
        ctx.strokeStyle = '#5d6c7d';
        ctx.beginPath();
        ctx.moveTo(margin, axisY);
        ctx.lineTo(view.w - margin, axisY);
        ctx.moveTo(axisX, margin);
        ctx.lineTo(axisX, view.h - margin);
        ctx.stroke();
        ctx.fillStyle = '#c3ced9';
        ctx.font = '12px system-ui, sans-serif';
        if (options.xLabel) {
            ctx.textAlign = 'right';
            ctx.textBaseline = 'bottom';
            ctx.fillText(options.xLabel, view.w - margin, axisY - 5);
        }
        if (options.yLabel) {
            ctx.textAlign = 'left';
            ctx.textBaseline = 'top';
            ctx.fillText(options.yLabel, axisX + 6, margin);
        }
    }

    function stroke(o, fallback) {
        ctx.strokeStyle = (o && o.color) || fallback || '#60a5fa';
        ctx.lineWidth = (o && o.width) || 2;
        ctx.setLineDash((o && o.dash) || []);
    }

    const g = {
        ctx,
        px: (x) => view.px(x),
        py: (y) => view.py(y),
        curve(fn, o) {
            stroke(o);
            ctx.beginPath();
            let drawing = false;
            const from = view.wx(margin);
            const to = view.wx(view.w - margin);
            for (let i = 0; i <= 400; i++) {
                const x = from + ((to - from) * i) / 400;
                const y = fn(x);
                if (!Number.isFinite(y)) {
                    drawing = false;
                    continue;
                }
                if (drawing) ctx.lineTo(view.px(x), view.py(y));
                else ctx.moveTo(view.px(x), view.py(y));
                drawing = true;
            }
            ctx.stroke();
        },
        path(points, o) {
            if (points.length < 2) return;
            stroke(o, '#fbbf24');
            ctx.beginPath();
            points.forEach(([x, y], i) => (i ? ctx.lineTo(view.px(x), view.py(y)) : ctx.moveTo(view.px(x), view.py(y))));
            ctx.stroke();
        },
        segment(x1, y1, x2, y2, o) {
            stroke(o, '#c3ced9');
            ctx.beginPath();
            ctx.moveTo(view.px(x1), view.py(y1));
            ctx.lineTo(view.px(x2), view.py(y2));
            ctx.stroke();
        },
        arrow(x1, y1, x2, y2, o) {
            g.segment(x1, y1, x2, y2, o);
            const a = Math.atan2(view.py(y2) - view.py(y1), view.px(x2) - view.px(x1));
            ctx.setLineDash([]);
            ctx.beginPath();
            ctx.moveTo(view.px(x2), view.py(y2));
            ctx.lineTo(view.px(x2) - 9 * Math.cos(a - 0.4), view.py(y2) - 9 * Math.sin(a - 0.4));
            ctx.moveTo(view.px(x2), view.py(y2));
            ctx.lineTo(view.px(x2) - 9 * Math.cos(a + 0.4), view.py(y2) - 9 * Math.sin(a + 0.4));
            ctx.stroke();
        },
        circle(x, y, r, o) {
            ctx.beginPath();
            ctx.ellipse(view.px(x), view.py(y), r * view.sx, r * view.sy, 0, 0, Math.PI * 2);
            if (o && o.fill) {
                ctx.fillStyle = o.fill;
                ctx.fill();
            }
            stroke(o, '#9aa8b8');
            ctx.stroke();
        },
        point(x, y, o) {
            const radius = (o && o.radius) || 5;
            ctx.beginPath();
            ctx.arc(view.px(x), view.py(y), radius, 0, Math.PI * 2);
            ctx.fillStyle = (o && o.color) || '#f87171';
            ctx.fill();
            if (o && o.label) g.text(x, y, o.label, { dx: radius + 5, dy: -radius - 5 });
            if (o && o.name) hits.push({ name: o.name, description: o.description, x: view.px(x), y: view.py(y), r: radius });
        },
        rect(x, y, w, h, o) {
            const left = view.px(x);
            const top = view.py(y + h);
            const width = w * view.sx;
            const height = h * view.sy;
            ctx.fillStyle = (o && o.color) || '#60a5fa';
            ctx.fillRect(left, top, width, height);
            if (o && o.name) hits.push({ name: o.name, description: o.description, box: [left, top, width, height] });
        },
        text(x, y, value, o) {
            ctx.fillStyle = (o && o.color) || '#e9eef3';
            ctx.font = `${(o && o.size) || 13}px system-ui, sans-serif`;
            ctx.textAlign = (o && o.align) || 'left';
            ctx.textBaseline = 'middle';
            ctx.fillText(String(value), view.px(x) + ((o && o.dx) || 0), view.py(y) + ((o && o.dy) || 0));
        },
    };

    renderers.push(() => {
        ctx.clearRect(0, 0, view.w, view.h);
        ctx.setLineDash([]);
        if (showAxes) drawAxes();
        hits = [];
        for (const draw of drawers) draw(g);
        counts.parts = Math.max(counts.parts, new Set(hits.map((hit) => hit.name)).size);
        const chosen = hits.find((hit) => hit.name === selectedName);
        if (chosen) {
            ctx.setLineDash([]);
            ctx.strokeStyle = '#a9d0ff';
            ctx.lineWidth = 2;
            ctx.beginPath();
            if (chosen.box) ctx.rect(chosen.box[0] - 3, chosen.box[1] - 3, chosen.box[2] + 6, chosen.box[3] + 6);
            else ctx.arc(chosen.x, chosen.y, chosen.r + 5, 0, Math.PI * 2);
            ctx.stroke();
        }
    });

    function hitAt(x, y) {
        let best = null;
        for (const hit of hits) {
            let distance;
            if (hit.box) {
                const inside = x >= hit.box[0] && x <= hit.box[0] + hit.box[2] && y >= hit.box[1] && y <= hit.box[1] + hit.box[3];
                distance = inside ? 0 : Infinity;
            } else {
                distance = Math.hypot(x - hit.x, y - hit.y) - hit.r;
            }
            if (distance <= 8 && (!best || distance < best.distance)) best = { hit, distance };
        }
        return best && best.hit;
    }

    // pointer position inside the canvas
    function at(e) {
        const box = canvas.getBoundingClientRect();
        return [e.clientX - box.left, e.clientY - box.top];
    }

    let down = null;
    canvas.addEventListener('pointerdown', guarded((e) => {
        down = at(e);
        canvas.setPointerCapture(e.pointerId);
        if (dragHandler) dragHandler(view.wx(down[0]), view.wy(down[1]));
    }));
    canvas.addEventListener('pointermove', guarded((e) => {
        if (!down || !dragHandler) return;
        const [x, y] = at(e);
        dragHandler(view.wx(x), view.wy(y));
    }));
    canvas.addEventListener('pointerup', (e) => {
        const [x, y] = at(e);
        const still = down && Math.hypot(x - down[0], y - down[1]) <= 5;
        down = null;
        if (!still) return;
        const hit = hitAt(x, y);
        if (hit) select(hit.name, hit.description);
    });

    return {
        draw(fn) {
            drawers.push(fn);
        },
        onDrag(fn) {
            dragHandler = fn;
        },
        setRange(x, y) {
            if (x) xRange = x;
            if (y) yRange = y;
            layout();
        },
    };
}

window.__stage = { three, plot, slider, button, readout, caption, info, outcome, onFrame, panel, counts: () => ({ ...counts }) };
