/**
 * AURA 3D Learning Lab — Client Controller & WebGL Engine.
 * 
 * Features:
 * - 60 FPS Three.js WebGL Engine with procedural primitives & auto-framing
 * - Raycaster component picking with hover & click selection
 * - Dynamic operational animation sequencer (pulse, rotate, highlight, flow)
 * - Natural language & voice parsing integration (Web Speech API)
 * - Multi-stage AI model generation progress
 * - Study material reader with topic detection
 */

(function () {
    "use strict";

    // Global State
    let scene, camera, renderer, controls, raycaster, mouse;
    let currentModelSpec = null;
    let componentMeshes = new Map(); // id -> THREE.Mesh / Group
    let originalMaterials = new Map(); // id -> THREE.Material
    let connectionMeshes = [];
    let selectedComponentId = null;
    let hoveredComponentId = null;
    let isAutoSpinning = false;
    let showLabels = true;
    let labelSprites = [];

    // Animation State
    let animSteps = [];
    let currentAnimStep = 0;
    let isPlayingAnim = false;
    let animInterval = null;
    let isTourRunning = false;
    let tourIndex = 0;
    let tourInterval = null;

    // Voice & Speech
    let recognition = null;
    let isListening = false;
    let isTtsEnabled = true;

    // Document & Session context
    let documentContext = "";
    let sessionId = "default_user_session";
    let currentTeacherLesson = null;
    let currentQuiz = null;
    let quizUserAnswers = new Map();
    let pendingConfirmationId = null;

    // Webcam Hand Gesture Tracking State
    let isGestureActive = false;
    let gestureStream = null;
    let gestureAnimFrameId = null;
    let mpHands = null;
    let mpCamera = null;
    let lastHandPos = null;
    let lastHandPinchDist = null;
    let lastHandArea = null;
    let lastGestureActionTime = 0;

    // DOM Elements Cache
    const el = {
        container: document.getElementById("threejs-container"),
        currentTopicName: document.getElementById("current-topic-name"),
        hoverBadge: document.getElementById("hover-badge"),
        generationOverlay: document.getElementById("generation-overlay"),
        stageTitle: document.getElementById("stage-title"),
        stageSubtitle: document.getElementById("stage-subtitle"),
        // Header actions & Pipeline status
        btnHeaderTeacher: document.getElementById("btn-header-teacher"),
        btnHeaderQuiz: document.getElementById("btn-header-quiz"),
        btnHeaderGestures: document.getElementById("btn-header-gestures"),
        btnHeaderVision: document.getElementById("btn-header-vision"),
        headerOsStatus: document.getElementById("header-os-status"),
        pipelineStatusChip: document.getElementById("pipeline-status-chip"),
        pipelineStatusText: document.getElementById("pipeline-status-text"),
        // Webcam Hand Gesture Tracking HUD PIP
        gesturePip: document.getElementById("gesture-pip"),
        gesturePipClose: document.getElementById("gesture-pip-close"),
        gestureVideo: document.getElementById("gesture-video"),
        gestureCanvas: document.getElementById("gesture-canvas"),
        gestureStatusBadge: document.getElementById("gesture-status-badge"),
        // Animation
        animPlayPause: document.getElementById("anim-play-pause"),
        animPrev: document.getElementById("anim-prev"),
        animNext: document.getElementById("anim-next"),
        animReset: document.getElementById("anim-reset"),
        animStepBadge: document.getElementById("anim-step-badge"),
        animStepDesc: document.getElementById("anim-step-desc"),
        animBarFill: document.getElementById("anim-bar-fill"),
        animTourBtn: document.getElementById("anim-tour-btn"),
        // Inspector
        compName: document.getElementById("comp-name"),
        compColorChip: document.getElementById("comp-color-chip"),
        compRoleTag: document.getElementById("comp-role-tag"),
        compTypeTag: document.getElementById("comp-type-tag"),
        compDesc: document.getElementById("comp-desc"),
        compSpeakBtn: document.getElementById("comp-speak-btn"),
        compAskBtn: document.getElementById("comp-ask-btn"),
        componentsScrollList: document.getElementById("components-scroll-list"),
        componentCountBadge: document.getElementById("component-count-badge"),
        // Topics
        topicsSection: document.getElementById("topics-section"),
        topicsList: document.getElementById("topics-list"),
        // Chat
        chatMessages: document.getElementById("chat-messages"),
        mainPromptInput: document.getElementById("main-prompt-input"),
        sendPromptBtn: document.getElementById("send-prompt-btn"),
        voiceInputBtn: document.getElementById("voice-input-btn"),
        micIcon: document.getElementById("mic-icon"),
        fileUploadBtn: document.getElementById("file-upload-btn"),
        hiddenFileInput: document.getElementById("hidden-file-input"),
        btnVoiceToggle: document.getElementById("btn-voice-toggle"),
        ttsIcon: document.getElementById("tts-icon"),
        // Modals
        examplesModal: document.getElementById("examples-modal"),
        btnOpenExamples: document.getElementById("btn-open-examples"),
        examplesCloseBtn: document.getElementById("examples-close-btn"),
        examplesSearchInput: document.getElementById("examples-search-input"),
        categoryTabs: document.getElementById("category-tabs"),
        examplesCardsGrid: document.getElementById("examples-cards-grid"),
        uploadModal: document.getElementById("upload-modal"),
        btnUploadTrigger: document.getElementById("btn-upload-trigger"),
        uploadCloseBtn: document.getElementById("upload-close-btn"),
        uploadDropzone: document.getElementById("upload-dropzone"),
        browseFilesBtn: document.getElementById("browse-files-btn"),
        uploadStatus: document.getElementById("upload-status"),
        uploadStatusText: document.getElementById("upload-status-text"),
        // Telemetry
        telemetryCpu: document.getElementById("telemetry-cpu"),
        telemetryCpuBar: document.getElementById("telemetry-cpu-bar"),
        telemetryRam: document.getElementById("telemetry-ram"),
        telemetryRamBar: document.getElementById("telemetry-ram-bar"),
        // Right Panel 5-Tabs & Views
        tabBtnInspector: document.getElementById("tab-btn-inspector"),
        tabBtnReferences: document.getElementById("tab-btn-references"),
        tabBtnTeacher: document.getElementById("tab-btn-teacher"),
        tabBtnQuiz: document.getElementById("tab-btn-quiz"),
        tabBtnOs: document.getElementById("tab-btn-os"),
        refTabCount: document.getElementById("ref-tab-count"),
        viewInspector: document.getElementById("view-inspector"),
        viewReferences: document.getElementById("view-references"),
        viewTeacher: document.getElementById("view-teacher"),
        viewQuiz: document.getElementById("view-quiz"),
        viewOs: document.getElementById("view-os"),
        referenceGalleryGrid: document.getElementById("reference-gallery-grid"),
        refStatusBadge: document.getElementById("ref-status-badge"),
        // Teacher View Elements
        teacherTopicTitle: document.getElementById("teacher-topic-title"),
        teacherOverviewBox: document.getElementById("teacher-overview-box"),
        teacherPrincipleBox: document.getElementById("teacher-principle-box"),
        teacherComponentsList: document.getElementById("teacher-components-list"),
        teacherAnimationBox: document.getElementById("teacher-animation-box"),
        teacherAppsList: document.getElementById("teacher-apps-list"),
        teacherSocraticList: document.getElementById("teacher-socratic-list"),
        teacherReadBtn: document.getElementById("teacher-read-btn"),
        teacherGenerateBtn: document.getElementById("teacher-generate-btn"),
        teacherLevelSelect: document.getElementById("teacher-level-select"),
        // Quiz View Elements

        quizDifficultySelect: document.getElementById("quiz-difficulty-select"),
        btnRegenQuiz: document.getElementById("btn-regen-quiz"),
        quizScoreRatio: document.getElementById("quiz-score-ratio"),
        quizScoreFill: document.getElementById("quiz-score-fill"),
        quizFeedbackText: document.getElementById("quiz-feedback-text"),
        quizQuestionsList: document.getElementById("quiz-questions-list"),
        quizResetBtn: document.getElementById("quiz-reset-btn"),
        // Student Progress HUD Elements
        studentRankBadge: document.getElementById("student-rank-badge"),
        studentAccuracyVal: document.getElementById("student-accuracy-val"),
        studentStreakVal: document.getElementById("student-streak-val"),
        studentQuizzesVal: document.getElementById("student-quizzes-val"),
        studentQuestionsVal: document.getElementById("student-questions-val"),
        studentTopicsRow: document.getElementById("student-topics-row"),
        studentMasteredTags: document.getElementById("student-mastered-tags"),
        // OS View Elements
        osCustomInput: document.getElementById("os-custom-input"),
        btnExecOs: document.getElementById("btn-exec-os"),
        osResultBox: document.getElementById("os-result-box"),
        processTelemetrySection: document.getElementById("process-telemetry-section"),
        processTableWrapper: document.getElementById("process-table-wrapper"),
        auditCountBadge: document.getElementById("audit-count-badge"),
        auditLogContainer: document.getElementById("audit-log-container"),
        // Lightbox Modal
        imageLightboxModal: document.getElementById("image-lightbox-modal"),
        lightboxCloseBtn: document.getElementById("lightbox-close-btn"),
        lightboxImg: document.getElementById("lightbox-img"),
        lightboxCaption: document.getElementById("lightbox-caption"),
        lightboxSourceLink: document.getElementById("lightbox-source-link"),
        lightboxSourceBadge: document.getElementById("lightbox-source-badge"),
        // Vision Modal
        visionModal: document.getElementById("vision-modal"),
        visionCloseBtn: document.getElementById("vision-close-btn"),
        visionDropzone: document.getElementById("vision-dropzone"),
        visionBrowseBtn: document.getElementById("vision-browse-btn"),
        visionFileInput: document.getElementById("vision-file-input"),
        visionPreviewBox: document.getElementById("vision-preview-box"),
        visionPreviewImg: document.getElementById("vision-preview-img"),
        visionPromptInput: document.getElementById("vision-prompt-input"),
        visionSubmitBtn: document.getElementById("vision-submit-btn"),
        visionStatus: document.getElementById("vision-status"),
        visionStatusText: document.getElementById("vision-status-text"),
        // OS Confirm Modal
        osConfirmModal: document.getElementById("os-confirm-modal"),
        confirmCloseBtn: document.getElementById("confirm-close-btn"),
        confirmModalText: document.getElementById("confirm-modal-text"),
        confirmDetailsBox: document.getElementById("confirm-details-box"),
        btnConfirmYes: document.getElementById("btn-confirm-yes"),
        btnConfirmNo: document.getElementById("btn-confirm-no"),
    };

    // ==========================================
    // 1. THREE.JS INITIALIZATION & SCENE SETUP
    // ==========================================

    function initThreeJS() {
        const width = el.container.clientWidth || window.innerWidth;
        const height = el.container.clientHeight || window.innerHeight;

        // Scene
        scene = new THREE.Scene();
        scene.background = new THREE.Color(0x060c14);

        // Camera
        camera = new THREE.PerspectiveCamera(48, width / height, 0.1, 1000);
        camera.position.set(7.5, 5.5, 7.5);

        // Renderer
        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setSize(width, height);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        el.container.appendChild(renderer.domElement);

        // OrbitControls
        controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.maxDistance = 50;
        controls.minDistance = 1.5;

        // Lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.65);
        scene.add(ambientLight);

        const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.9);
        dirLight1.position.set(10, 15, 10);
        scene.add(dirLight1);

        const dirLight2 = new THREE.DirectionalLight(0x00d4ff, 0.4);
        dirLight2.position.set(-10, -5, -10);
        scene.add(dirLight2);

        // Subtle orange rim light for tech aesthetic
        const rimLight = new THREE.PointLight(0xff8c00, 0.8, 25);
        rimLight.position.set(0, 10, 0);
        scene.add(rimLight);

        // Grid Plane
        const grid = new THREE.GridHelper(16, 24, 0x153c54, 0x091d2d);
        grid.position.y = -2.2;
        scene.add(grid);

        // Raycaster
        raycaster = new THREE.Raycaster();
        mouse = new THREE.Vector2(-1000, -1000);

        // Events
        window.addEventListener("resize", onWindowResize);
        el.container.addEventListener("mousemove", onMouseMove);
        el.container.addEventListener("click", onMouseClick);

        // Viewport toolbar buttons
        document.getElementById("v-zoom-in").addEventListener("click", () => zoomCamera(-1.5));
        document.getElementById("v-zoom-out").addEventListener("click", () => zoomCamera(1.5));
        document.getElementById("v-rotate").addEventListener("click", () => rotateCamera(Math.PI / 4));
        document.getElementById("v-auto-spin").addEventListener("click", toggleAutoSpin);
        document.getElementById("v-recenter").addEventListener("click", () => fitCameraToObject(scene));
        document.getElementById("btn-reset-view").addEventListener("click", () => fitCameraToObject(scene));

        // Start Animation Loop
        animateLoop();
    }

    function onWindowResize() {
        if (!camera || !renderer || !el.container) return;
        const width = el.container.clientWidth;
        const height = el.container.clientHeight;
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height);
    }

    function animateLoop() {
        requestAnimationFrame(animateLoop);

        if (isAutoSpinning && controls) {
            controls.autoRotate = true;
            controls.autoRotateSpeed = 2.0;
        } else if (controls) {
            controls.autoRotate = false;
        }

        controls.update();

        // Continuous 60 FPS Physics-Informed Semantic Animation Loop
        if (isPlayingAnim && currentModelSpec) {
            const time = Date.now() * 0.003;
            const activeStep = animSteps[currentAnimStep];
            if (activeStep) {
                const action = (activeStep.action || "pulse").toLowerCase();
                const params = activeStep.params || {};
                const intensity = activeStep.intensity || 1.0;

                (activeStep.affected_components || []).forEach(cid => {
                    const mesh = componentMeshes.get(cid);
                    if (!mesh) return;

                    switch (action) {
                        case "mechanical_rotation": {
                            // Smooth angular rotation around designated axis
                            const rpm = params.rpm || 45.0;
                            const radPerFrame = (rpm * 2 * Math.PI) / (60 * 60) * intensity;
                            const axis = (params.axis || "z").toLowerCase();
                            if (axis === "x") mesh.rotation.x += radPerFrame;
                            else if (axis === "y") mesh.rotation.y += radPerFrame;
                            else mesh.rotation.z += radPerFrame;
                            break;
                        }
                        case "electrical_flow": {
                            // Pulsing emissive luminous glow & subtle high-frequency vibration
                            const glow = 0.4 + 0.45 * Math.sin(time * 12);
                            if (mesh.material && mesh.material.emissive) {
                                mesh.material.emissive = new THREE.Color(params.color || "#00ffff");
                                mesh.material.emissiveIntensity = glow * intensity;
                            }
                            // Dash pulse along conduits connected to this component
                            connectionMeshes.forEach(conduit => {
                                if (conduit.material && conduit.material.emissive) {
                                    conduit.material.emissiveIntensity = (0.5 + 0.5 * Math.sin(time * 16)) * intensity;
                                }
                            });
                            break;
                        }
                        case "magnetic_flux": {
                            // Undulating flux ripple with magnetic field breathing
                            const fluxWave = 1.0 + 0.12 * Math.sin(time * 6 * (params.frequency || 1.5)) * intensity;
                            mesh.scale.set(fluxWave, fluxWave, fluxWave);
                            if (mesh.material && mesh.material.emissive) {
                                mesh.material.emissive = new THREE.Color(params.color || "#ffaa00");
                                mesh.material.emissiveIntensity = 0.35 + 0.3 * Math.cos(time * 6);
                            }
                            break;
                        }
                        case "fluid_flow": {
                            // Directional fluid pulse along mesh
                            const flowOffset = Math.sin(time * 8 * (params.speed || 1.0));
                            const flowScale = 1.0 + 0.05 * flowOffset * intensity;
                            mesh.scale.set(flowScale, flowScale, flowScale);
                            if (mesh.material && mesh.material.color) {
                                const baseColor = new THREE.Color(params.color || "#00e5ff");
                                mesh.material.color.lerp(baseColor, 0.1);
                            }
                            break;
                        }
                        case "heat_transfer": {
                            // Dynamic thermodynamic shift between cold blue and incandescence red/orange
                            const heatT = (Math.sin(time * 4) + 1.0) / 2.0; // 0 to 1
                            const coldColor = new THREE.Color("#0088ff");
                            const hotColor = new THREE.Color(params.color || "#ff3300");
                            if (mesh.material && mesh.material.emissive) {
                                mesh.material.emissive = coldColor.clone().lerp(hotColor, heatT);
                                mesh.material.emissiveIntensity = (0.2 + 0.6 * heatT) * intensity;
                            }
                            break;
                        }
                        case "signal_propagation": {
                            // Concentric pulsing wave emission
                            const sigPulse = (time * 5) % Math.PI;
                            const sigScale = 1.0 + 0.18 * Math.sin(sigPulse) * intensity;
                            mesh.scale.set(sigScale, sigScale, sigScale);
                            if (mesh.material && mesh.material.emissive) {
                                mesh.material.emissive = new THREE.Color("#a855f7");
                                mesh.material.emissiveIntensity = (1.0 - (sigPulse / Math.PI)) * 0.7;
                            }
                            break;
                        }
                        case "force_motion": {
                            // Reciprocating mechanical stroke displacement (piston/pushrod)
                            const strokeDist = 0.18 * Math.sin(time * 7) * intensity;
                            if (mesh.userData.basePosition) {
                                mesh.position.z = mesh.userData.basePosition.z + strokeDist;
                            } else {
                                mesh.userData.basePosition = mesh.position.clone();
                            }
                            break;
                        }
                        case "biological_flow": {
                            // Rhythmic biological heartbeat oscillation (systole / diastole)
                            const beat = Math.pow(Math.sin(time * 4.5), 63);
                            const bioScale = 1.0 + 0.12 * Math.sin(time * 4.5) + 0.15 * beat * intensity;
                            mesh.scale.set(bioScale, bioScale, bioScale);
                            if (mesh.material && mesh.material.emissive) {
                                mesh.material.emissive = new THREE.Color("#ff1744");
                                mesh.material.emissiveIntensity = 0.2 + 0.6 * beat;
                            }
                            break;
                        }
                        case "rotate": {
                            mesh.rotation.y += 0.03 * intensity;
                            break;
                        }
                        case "pulse":
                        default: {
                            const scale = 1.0 + 0.08 * Math.sin(time * 4) * intensity;
                            mesh.scale.set(scale, scale, scale);
                            break;
                        }
                    }
                });
            }
        }

        renderer.render(scene, camera);
    }

    function zoomCamera(delta) {
        const factor = delta > 0 ? 1.2 : 0.8;
        camera.position.multiplyScalar(factor);
        controls.update();
    }

    function rotateCamera(angle) {
        const x = camera.position.x;
        const z = camera.position.z;
        camera.position.x = x * Math.cos(angle) - z * Math.sin(angle);
        camera.position.z = x * Math.sin(angle) + z * Math.cos(angle);
        camera.lookAt(controls.target);
        controls.update();
    }

    function orbitCameraByDelta(dx, dy) {
        if (!controls || !camera) return;
        const offset = camera.position.clone().sub(controls.target);
        const radius = offset.length();
        if (radius < 0.001) return;
        let theta = Math.atan2(offset.x, offset.z);
        let phi = Math.acos(Math.max(-1, Math.min(1, offset.y / radius)));

        // dx: horizontal rotation around target (webcam mirrored)
        theta -= dx * 3.5;
        // dy: vertical elevation
        phi -= dy * 2.8;
        phi = Math.max(0.08, Math.min(Math.PI - 0.08, phi));

        offset.x = radius * Math.sin(phi) * Math.sin(theta);
        offset.y = radius * Math.cos(phi);
        offset.z = radius * Math.sin(phi) * Math.cos(theta);

        camera.position.copy(controls.target).add(offset);
        camera.lookAt(controls.target);
        controls.update();
    }

    function zoomCameraByDelta(delta) {
        if (!controls || !camera) return;
        const offset = camera.position.clone().sub(controls.target);
        const factor = 1.0 + delta * 0.06;
        const clampedFactor = Math.max(0.75, Math.min(1.35, factor));
        offset.multiplyScalar(clampedFactor);
        const dist = offset.length();
        if (dist >= (controls.minDistance || 1.5) && dist <= (controls.maxDistance || 50)) {
            camera.position.copy(controls.target).add(offset);
            controls.update();
        }
    }

    function resetCameraView() {
        if (scene) {
            fitCameraToObject(scene);
            if (controls) controls.update();
        }
    }

    function toggleAutoSpin() {
        isAutoSpinning = !isAutoSpinning;
        document.getElementById("v-auto-spin").style.color = isAutoSpinning ? "var(--pri-orange)" : "var(--sec-cyan)";
    }

    // ==========================================
    // 2. 3D MODEL RENDERING & GEOMETRY BUILDERS
    // ==========================================

    function clearScene() {
        // Dispose existing meshes
        componentMeshes.forEach(mesh => {
            scene.remove(mesh);
            if (mesh.geometry) mesh.geometry.dispose();
            if (mesh.material) {
                if (Array.isArray(mesh.material)) mesh.material.forEach(m => m.dispose());
                else mesh.material.dispose();
            }
        });
        componentMeshes.clear();
        originalMaterials.clear();

        connectionMeshes.forEach(m => {
            scene.remove(m);
            if (m.geometry) m.geometry.dispose();
            if (m.material) m.material.dispose();
        });
        connectionMeshes = [];

        labelSprites.forEach(s => scene.remove(s));
        labelSprites = [];
    }

    function renderModelSpec(spec) {
        clearScene();
        currentModelSpec = spec;
        el.currentTopicName.textContent = spec.topic || "3D System";

        // 1. Build Components
        const components = spec.components || [];
        components.forEach((c, idx) => {
            const mesh = createComponentMesh(c);
            if (mesh) {
                mesh.userData = { id: c.id, spec: c };
                scene.add(mesh);
                componentMeshes.set(c.id, mesh);
                originalMaterials.set(c.id, mesh.material.clone());

                // Create billboard label if enabled
                if (showLabels) {
                    const labelSprite = createTextBillboard(c.name || c.id, c.position, c.color || "#00d4ff");
                    if (labelSprite) {
                        scene.add(labelSprite);
                        labelSprites.push(labelSprite);
                    }
                }
            }
        });

        // 2. Build Physical Conduits & Connections
        const connections = spec.connections || [];
        connections.forEach(conn => {
            const c1 = components.find(c => c.id === conn.from_id);
            const c2 = components.find(c => c.id === conn.to_id);
            if (c1 && c2 && c1.position && c2.position) {
                const conduit = createConduitBetween(
                    c1.position,
                    c2.position,
                    conn.color || "#00d4ff",
                    conn.thickness || 2.5
                );
                if (conduit) {
                    scene.add(conduit);
                    connectionMeshes.push(conduit);
                }
            }
        });

        // 3. Populate Parts Explorer List
        populatePartsList(components);

        // 4. Setup Animation Steps
        setupAnimationSequence(spec.animation_steps || []);

        // 5. Center and Fit Camera
        fitCameraToObject(scene);

        // 6. Select first component by default
        if (components.length > 0) {
            selectComponent(components[0].id, false);
        }

        // 7. Render Real-World Reference Images Gallery for Side-by-Side Comparison
        renderReferenceGallery(spec.reference_images || [], spec.topic || "3D System");

        // 8. Auto-load or generate Interactive Option Quiz
        if (spec.quiz) {
            renderQuiz(spec.quiz);
        } else {
            regenerateQuiz();
        }
    }

    function createComponentMesh(c) {
        const type = (c.type || "box").toLowerCase();
        const pos = c.position || [0, 0, 0];
        const color = c.color || "#00d4ff";
        const alpha = c.alpha !== undefined ? c.alpha : 0.9;

        const material = new THREE.MeshStandardMaterial({
            color: new THREE.Color(color),
            metalness: 0.35,
            roughness: 0.35,
            transparent: alpha < 1.0,
            opacity: alpha,
        });

        let geometry;

        // Arbitrary 3D cylinder between endpoints
        if (c.endpoints && c.endpoints.length >= 2) {
            const p1 = new THREE.Vector3(...c.endpoints[0]);
            const p2 = new THREE.Vector3(...c.endpoints[1]);
            const radius = typeof c.size === "number" ? c.size : (Array.isArray(c.size) ? c.size[0] : 0.15);
            return createCylinderBetweenPoints(p1, p2, radius, material);
        }

        switch (type) {
            case "sphere": {
                const r = typeof c.size === "number" ? c.size : (Array.isArray(c.size) ? c.size[0] : 0.5);
                geometry = new THREE.SphereGeometry(Math.max(0.08, r), 32, 24);
                break;
            }
            case "cylinder": {
                let r = 0.4, h = 1.6;
                if (Array.isArray(c.size)) {
                    r = c.size[0] || 0.4;
                    h = c.size[1] || 1.6;
                } else if (typeof c.size === "number") {
                    r = c.size;
                }
                geometry = new THREE.CylinderGeometry(Math.max(0.05, r), Math.max(0.05, r), Math.max(0.1, h), 32);
                break;
            }
            case "torus": {
                let r = 1.2, tube = 0.08;
                if (Array.isArray(c.size)) {
                    r = c.size[0] || 1.2;
                    tube = c.size[1] || 0.08;
                }
                geometry = new THREE.TorusGeometry(Math.max(0.2, r), Math.max(0.02, tube), 16, 48);
                break;
            }
            case "cone": {
                let r = 0.5, h = 1.2;
                if (Array.isArray(c.size)) {
                    r = c.size[0] || 0.5;
                    h = c.size[1] || 1.2;
                }
                geometry = new THREE.ConeGeometry(Math.max(0.1, r), Math.max(0.1, h), 32);
                break;
            }
            case "box":
            default: {
                let w = 1.0, h = 1.0, d = 1.0;
                if (Array.isArray(c.size)) {
                    w = c.size[0] || 1.0;
                    h = c.size[1] || w;
                    d = c.size[2] || w;
                } else if (typeof c.size === "number") {
                    w = h = d = c.size;
                }
                geometry = new THREE.BoxGeometry(Math.max(0.1, w), Math.max(0.1, h), Math.max(0.1, d));
                break;
            }
        }

        const mesh = new THREE.Mesh(geometry, material);
        mesh.position.set(pos[0], pos[1], pos[2]);

        // Orientation / Axis
        if (type === "cylinder") {
            const axis = (c.axis || "z").toLowerCase();
            if (axis === "x") mesh.rotation.z = Math.PI / 2;
            else if (axis === "z") mesh.rotation.x = Math.PI / 2;
        } else if (type === "torus" && c.normal) {
            const norm = new THREE.Vector3(...c.normal).normalize();
            mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), norm);
        }

        mesh.castShadow = true;
        mesh.receiveShadow = true;
        return mesh;
    }

    function createCylinderBetweenPoints(p1, p2, radius, material) {
        const v = new THREE.Vector3().subVectors(p2, p1);
        const length = v.length();
        if (length < 0.001) return null;

        const geometry = new THREE.CylinderGeometry(radius, radius, length, 24);
        const mesh = new THREE.Mesh(geometry, material);

        const midpoint = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
        mesh.position.copy(midpoint);

        const yAxis = new THREE.Vector3(0, 1, 0);
        mesh.quaternion.setFromUnitVectors(yAxis, v.clone().normalize());

        mesh.castShadow = true;
        return mesh;
    }

    function createConduitBetween(pos1, pos2, colorHex, thickness) {
        const group = new THREE.Group();
        const p1 = new THREE.Vector3(...pos1);
        const p2 = new THREE.Vector3(...pos2);
        const radius = Math.max(0.02, 0.015 * thickness);

        const material = new THREE.MeshStandardMaterial({
            color: new THREE.Color(colorHex),
            metalness: 0.5,
            roughness: 0.3,
            transparent: true,
            opacity: 0.85,
        });

        // Conduit cylinder
        const cylinder = createCylinderBetweenPoints(p1, p2, radius, material);
        if (cylinder) group.add(cylinder);

        // Junction spheres
        const sphereGeo = new THREE.SphereGeometry(radius * 1.6, 16, 16);
        const s1 = new THREE.Mesh(sphereGeo, material);
        s1.position.copy(p1);
        group.add(s1);

        const s2 = new THREE.Mesh(sphereGeo, material);
        s2.position.copy(p2);
        group.add(s2);

        return group;
    }

    function createTextBillboard(text, pos, color) {
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");
        canvas.width = 256;
        canvas.height = 64;

        ctx.fillStyle = "rgba(9, 20, 31, 0.85)";
        ctx.strokeStyle = color;
        ctx.lineWidth = 3;
        ctx.roundRect(4, 4, 248, 56, 8);
        ctx.fill();
        ctx.stroke();

        ctx.font = "bold 22px 'Rajdhani', sans-serif";
        ctx.fillStyle = "#ffffff";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(text, 128, 32);

        const texture = new THREE.CanvasTexture(canvas);
        const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
        const sprite = new THREE.Sprite(spriteMat);
        sprite.position.set(pos[0], pos[1] + 0.6, pos[2]);
        sprite.scale.set(1.4, 0.35, 1);
        return sprite;
    }

    function fitCameraToObject(rootObject) {
        const box = new THREE.Box3().setFromObject(rootObject);
        if (box.isEmpty()) return;

        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z, 2.5);

        const fov = camera.fov * (Math.PI / 180);
        let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2)) * 1.4;
        cameraZ = Math.max(cameraZ, 4.0);

        camera.position.set(center.x + cameraZ * 0.8, center.y + cameraZ * 0.6, center.z + cameraZ);
        camera.lookAt(center);
        controls.target.copy(center);
        controls.update();
    }

    // ==========================================
    // 3. COMPONENT INTERACTION & RAYCASTING
    // ==========================================

    function onMouseMove(event) {
        const rect = renderer.domElement.getBoundingClientRect();
        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        raycaster.setFromCamera(mouse, camera);
        const meshes = Array.from(componentMeshes.values());
        const intersects = raycaster.intersectObjects(meshes, true);

        if (intersects.length > 0) {
            let hit = intersects[0].object;
            while (hit.parent && !hit.userData.id && hit.parent !== scene) {
                hit = hit.parent;
            }
            const compId = hit.userData.id;
            if (compId) {
                el.container.style.cursor = "pointer";
                hoveredComponentId = compId;
                const comp = (currentModelSpec.components || []).find(c => c.id === compId);
                if (comp) {
                    el.hoverBadge.textContent = comp.name || comp.id;
                    el.hoverBadge.style.display = "block";
                    el.hoverBadge.style.left = `${event.clientX - rect.left + 15}px`;
                    el.hoverBadge.style.top = `${event.clientY - rect.top + 15}px`;
                }
                return;
            }
        }

        el.container.style.cursor = "default";
        el.hoverBadge.style.display = "none";
        hoveredComponentId = null;
    }

    function onMouseClick(event) {
        if (!hoveredComponentId) return;
        selectComponent(hoveredComponentId, true);
    }

    function selectComponent(id, speak = true) {
        selectedComponentId = id;
        const comp = (currentModelSpec.components || []).find(c => c.id === id);
        if (!comp) return;

        // 1. Reset previous mesh colors and highlight selected
        componentMeshes.forEach((mesh, cid) => {
            const orig = originalMaterials.get(cid);
            if (orig) {
                if (cid === id) {
                    mesh.material = new THREE.MeshStandardMaterial({
                        color: new THREE.Color("#ff8c00"),
                        emissive: new THREE.Color("#ff8c00"),
                        emissiveIntensity: 0.45,
                        metalness: 0.6,
                        roughness: 0.2,
                    });
                } else {
                    mesh.material = orig.clone();
                }
            }
        });

        // 2. Update Inspector Card
        el.compName.textContent = comp.name || comp.id;
        el.compColorChip.style.backgroundColor = comp.color || "#00d4ff";
        el.compRoleTag.textContent = `Role: ${comp.role || "Active"}`;
        el.compTypeTag.textContent = `Type: ${comp.type || "Solid"}`;
        el.compDesc.textContent = comp.description || "Active component in system.";

        // 3. Highlight in parts list
        document.querySelectorAll(".comp-item").forEach(item => {
            item.classList.toggle("selected", item.dataset.id === id);
        });

        // 4. TTS Read Aloud if enabled
        if (speak && isTtsEnabled) {
            speakText(`${comp.name}. ${comp.description}`);
        }

        // 5. Smooth Camera Focus on Selected Component
        const selectedMesh = componentMeshes.get(id);
        if (selectedMesh) {
            focusCameraOnComponent(selectedMesh);
        }
    }

    function focusCameraOnComponent(mesh) {
        if (!mesh || !controls || !camera) return;
        const targetPos = new THREE.Vector3();
        mesh.getWorldPosition(targetPos);

        const startTarget = controls.target.clone();
        const duration = 350;
        const startTime = performance.now();

        function animateFocus(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(1.0, elapsed / duration);
            const ease = 0.5 - 0.5 * Math.cos(progress * Math.PI);

            controls.target.lerpVectors(startTarget, targetPos, ease);
            controls.update();

            if (progress < 1.0) {
                requestAnimationFrame(animateFocus);
            }
        }
        requestAnimationFrame(animateFocus);
    }


    function populatePartsList(components) {
        el.componentsScrollList.innerHTML = "";
        el.componentCountBadge.textContent = `${components.length} PARTS`;

        components.forEach(c => {
            const item = document.createElement("div");
            item.className = "comp-item";
            item.dataset.id = c.id;
            item.innerHTML = `
                <div class="comp-dot" style="background-color: ${c.color || '#00d4ff'};"></div>
                <div class="comp-item-name">${c.name || c.id}</div>
            `;
            item.addEventListener("click", () => selectComponent(c.id, true));
            el.componentsScrollList.appendChild(item);
        });
    }

    // ==========================================
    // 3b. REAL-WORLD REFERENCE GALLERY & LIGHTBOX
    // ==========================================

    function switchRightPanelTab(tab) {
        const tabs = ["inspector", "references", "teacher", "quiz", "os"];
        const btns = {
            inspector: el.tabBtnInspector,
            references: el.tabBtnReferences,
            teacher: el.tabBtnTeacher,
            quiz: el.tabBtnQuiz,
            os: el.tabBtnOs,
        };
        const views = {
            inspector: el.viewInspector,
            references: el.viewReferences,
            teacher: el.viewTeacher,
            quiz: el.viewQuiz,
            os: el.viewOs,
        };

        tabs.forEach(t => {
            if (btns[t]) btns[t].classList.toggle("active", t === tab);
            if (views[t]) views[t].style.display = (t === tab) ? "flex" : "none";
        });

        if (tab === "os") {
            loadOsStatus();
        }
        if (tab === "quiz") {
            loadStudentProgress();
            if (!currentQuiz || !el.quizQuestionsList || el.quizQuestionsList.children.length === 0) {
                regenerateQuiz();
            }
        }
    }

    async function renderReferenceGallery(images, topic) {
        if (!el.referenceGalleryGrid) return;
        el.referenceGalleryGrid.innerHTML = "";

        let imgList = Array.isArray(images) ? [...images] : [];

        // If no images attached to ModelSpec, dynamically query the search endpoint
        if (imgList.length === 0 && topic) {
            try {
                if (el.refStatusBadge) el.refStatusBadge.textContent = "SEARCHING...";
                const res = await fetch(`/api/images/search?query=${encodeURIComponent(topic)}`);
                if (res.ok) {
                    const data = await res.json();
                    imgList = data.images || [];
                }
            } catch (err) {
                console.warn("Could not fetch reference schematics:", err);
            }
        }

        if (el.refStatusBadge) {
            el.refStatusBadge.textContent = imgList.length > 0 ? "ONLINE" : "OFFLINE";
        }
        if (el.refTabCount) {
            el.refTabCount.textContent = imgList.length;
        }

        if (imgList.length === 0) {
            el.referenceGalleryGrid.innerHTML = `
                <div class="ref-empty-state">
                    No web schematics found for <strong>${topic || "this topic"}</strong>.<br>
                    You can inspect all generated 3D components in the PARTS & SPECS tab.
                </div>
            `;
            return;
        }

        imgList.forEach((item) => {
            const card = document.createElement("div");
            card.className = "ref-card";
            card.title = "Click to enlarge and compare side-by-side with 3D model";

            let domain = "";
            try {
                if (item.source) {
                    domain = new URL(item.source).hostname.replace(/^www\./, "");
                }
            } catch (e) {
                domain = "Web Source";
            }

            const imgUrl = item.thumbnail || item.image;
            const fullImg = item.image || item.thumbnail;

            card.innerHTML = `
                <div class="ref-thumb-box">
                    <img class="ref-thumb-img" src="${imgUrl}" alt="${item.title || topic}" loading="lazy">
                    <div class="ref-card-overlay">
                        <span>🔍 ENLARGE & COMPARE</span>
                    </div>
                </div>
                <div class="ref-card-info">
                    <div class="ref-card-title">${item.title || `${topic} Technical Diagram`}</div>
                    <div class="ref-card-source">${domain || "Reference Schematic"}</div>
                </div>
            `;

            // Gracefully handle broken image URLs with SVG technical placeholder
            const imgEl = card.querySelector(".ref-thumb-img");
            if (imgEl) {
                imgEl.onerror = () => {
                    imgEl.src = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='120' viewBox='0 0 200 120'><rect width='200' height='120' fill='%2305101a'/><text x='50%25' y='50%25' fill='%2300d4ff' font-family='monospace' font-size='11' text-anchor='middle' dy='.3em'>Schematic Diagram</text></svg>";
                };
            }

            card.addEventListener("click", () => {
                openImageLightbox({
                    image: fullImg,
                    title: item.title || `${topic} Schematic`,
                    source: item.source || fullImg,
                }, topic);
            });

            el.referenceGalleryGrid.appendChild(card);
        });
    }

    function openImageLightbox(imgData, topic) {
        if (!el.imageLightboxModal) return;

        if (el.lightboxImg) {
            el.lightboxImg.src = imgData.image;
            el.lightboxImg.alt = imgData.title || topic;
            el.lightboxImg.onerror = () => {
                el.lightboxImg.src = imgData.thumbnail || "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='400' height='300' viewBox='0 0 400 300'><rect width='400' height='300' fill='%2305101a'/><text x='50%25' y='50%25' fill='%2300d4ff' font-family='monospace' font-size='14' text-anchor='middle' dy='.3em'>Schematic Diagram</text></svg>";
            };
        }
        if (el.lightboxCaption) {
            el.lightboxCaption.textContent = imgData.title || `${topic} Reference Schematic`;
        }
        if (el.lightboxSourceLink) {
            el.lightboxSourceLink.href = imgData.source || imgData.image;
        }

        el.imageLightboxModal.style.display = "flex";
    }

    function closeImageLightbox() {
        if (el.imageLightboxModal) {
            el.imageLightboxModal.style.display = "none";
        }
    }

    // ==========================================
    // 4. DYNAMIC ANIMATION SEQUENCER
    // ==========================================

    function setupAnimationSequence(steps) {
        animSteps = steps || [];
        currentAnimStep = 0;
        isPlayingAnim = false;
        clearInterval(animInterval);
        el.animPlayPause.textContent = "▶ PLAY";

        updateAnimationUI();
    }

    function updateAnimationUI() {
        if (!animSteps || animSteps.length === 0) {
            el.animStepBadge.textContent = "NO ANIMATION";
            el.animStepDesc.textContent = "Static model inspection.";
            el.animBarFill.style.width = "100%";
            return;
        }

        const step = animSteps[currentAnimStep];
        el.animStepBadge.textContent = `STEP ${currentAnimStep + 1} OF ${animSteps.length}`;
        el.animStepDesc.textContent = step ? step.description : "";
        const progress = ((currentAnimStep + 1) / animSteps.length) * 100;
        el.animBarFill.style.width = `${progress}%`;

        // Highlight affected components
        if (step && step.affected_components) {
            step.affected_components.forEach(cid => {
                const mesh = componentMeshes.get(cid);
                if (mesh) {
                    mesh.material = new THREE.MeshStandardMaterial({
                        color: new THREE.Color("#ffcc00"),
                        emissive: new THREE.Color("#ff8c00"),
                        emissiveIntensity: 0.3,
                    });
                }
            });
        }
    }

    function playAnimation() {
        if (!animSteps || animSteps.length === 0) return;
        isPlayingAnim = true;
        el.animPlayPause.textContent = "⏸ PAUSE";

        clearInterval(animInterval);
        animInterval = setInterval(() => {
            currentAnimStep = (currentAnimStep + 1) % animSteps.length;
            updateAnimationUI();
        }, 2200);
    }

    function pauseAnimation() {
        isPlayingAnim = false;
        el.animPlayPause.textContent = "▶ PLAY";
        clearInterval(animInterval);
        // Reset mesh scales
        componentMeshes.forEach(mesh => mesh.scale.set(1, 1, 1));
    }

    function nextAnimStep() {
        pauseAnimation();
        if (animSteps.length > 0) {
            currentAnimStep = (currentAnimStep + 1) % animSteps.length;
            updateAnimationUI();
        }
    }

    function prevAnimStep() {
        pauseAnimation();
        if (animSteps.length > 0) {
            currentAnimStep = (currentAnimStep - 1 + animSteps.length) % animSteps.length;
            updateAnimationUI();
        }
    }

    function resetAnimation() {
        pauseAnimation();
        currentAnimStep = 0;
        updateAnimationUI();
        if (currentModelSpec && currentModelSpec.components.length > 0) {
            selectComponent(currentModelSpec.components[0].id, false);
        }
    }

    function startPartsTour() {
        if (!currentModelSpec || !currentModelSpec.components) return;
        const comps = currentModelSpec.components;
        if (comps.length === 0) return;

        pauseAnimation();
        isTourRunning = true;
        tourIndex = 0;

        selectComponent(comps[tourIndex].id, true);

        clearInterval(tourInterval);
        tourInterval = setInterval(() => {
            tourIndex++;
            if (tourIndex >= comps.length) {
                clearInterval(tourInterval);
                isTourRunning = false;
                appendChatMessage("AURA", "Completed the 3D parts tour.");
                return;
            }
            selectComponent(comps[tourIndex].id, true);
        }, 3200);
    }

    // ==========================================
    // 4b. AI TEACHER MODE
    // ==========================================

    function renderTeacherLesson(lesson) {
        if (!lesson) return;
        currentTeacherLesson = lesson;

        if (el.teacherTopicTitle) el.teacherTopicTitle.textContent = lesson.topic || (currentModelSpec ? currentModelSpec.topic : "System");
        if (el.teacherOverviewBox) el.teacherOverviewBox.textContent = lesson.overview || "Overview of the active system.";
        if (el.teacherPrincipleBox) el.teacherPrincipleBox.textContent = lesson.working_principle || "Governed by fundamental physical conservation laws.";
        if (el.teacherAnimationBox) el.teacherAnimationBox.textContent = lesson.animation_analysis || "Operational phase sequence.";

        // Components breakdown
        if (el.teacherComponentsList) {
            el.teacherComponentsList.innerHTML = "";
            const comps = lesson.components_breakdown || [];
            comps.forEach(c => {
                const item = document.createElement("div");
                item.className = "teacher-breakdown-item";
                item.innerHTML = `
                    <div class="teacher-breakdown-name">${c.name}</div>
                    <div class="teacher-breakdown-role">${c.role || "Operational Component"}</div>
                    <div class="teacher-breakdown-desc">${c.explanation}</div>
                `;
                el.teacherComponentsList.appendChild(item);
            });
        }

        // Applications
        if (el.teacherAppsList) {
            el.teacherAppsList.innerHTML = "";
            const apps = lesson.real_world_applications || [];
            apps.forEach(app => {
                const item = document.createElement("div");
                item.className = "teacher-app-item";
                item.textContent = `• ${app}`;
                el.teacherAppsList.appendChild(item);
            });
        }

        // Socratic Questions
        if (el.teacherSocraticList) {
            el.teacherSocraticList.innerHTML = "";
            const qList = lesson.socratic_questions || [];
            qList.forEach((q, idx) => {
                const card = document.createElement("div");
                card.className = "socratic-card";
                card.innerHTML = `
                    <div class="socratic-question">Q${idx + 1}: ${q.question}</div>
                    <div class="socratic-actions">
                        <button class="socratic-toggle-btn hint-btn">💡 Clue / Hint</button>
                        <button class="socratic-toggle-btn ans-btn">✓ Master Answer</button>
                    </div>
                    <div class="socratic-hint-box" style="display: none;">${q.hint || "Analyze energy transformation and dimensions."}</div>
                    <div class="socratic-answer-box" style="display: none;">${q.answer || "Answer based on physical principles."}</div>
                `;
                const hintBtn = card.querySelector(".hint-btn");
                const hintBox = card.querySelector(".socratic-hint-box");
                const ansBtn = card.querySelector(".ans-btn");
                const ansBox = card.querySelector(".socratic-answer-box");

                hintBtn.addEventListener("click", () => {
                    hintBox.style.display = hintBox.style.display === "none" ? "block" : "none";
                });
                ansBtn.addEventListener("click", () => {
                    ansBox.style.display = ansBox.style.display === "none" ? "block" : "none";
                });
                el.teacherSocraticList.appendChild(card);
            });
        }
    }

    function speakTeacherLesson() {
        if (!currentTeacherLesson) return;
        const text = `${currentTeacherLesson.topic}. ${currentTeacherLesson.overview} Working principle: ${currentTeacherLesson.working_principle}`;
        speakText(text);
    }

    async function refreshTeacherLesson() {
        if (!currentModelSpec) return;
        const level = (el.teacherLevelSelect && el.teacherLevelSelect.value) || "Intermediate";
        try {
            if (el.teacherStatusBadge) el.teacherStatusBadge.textContent = "SYNTHESIZING...";
            const resp = await fetch("/api/teacher/explain", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ model_spec: currentModelSpec, level: level }),
            });
            if (resp.ok) {
                const lesson = await resp.json();
                renderTeacherLesson(lesson);
                if (el.teacherStatusBadge) el.teacherStatusBadge.textContent = level.toUpperCase();
            }
        } catch (e) {
            console.error("Teacher refresh error:", e);
        }
    }


    // ==========================================
    // 4c. INTERACTIVE QUIZ LAB
    // ==========================================

    function renderQuiz(quizData) {
        if (!quizData) return;
        currentQuiz = quizData;
        quizUserAnswers.clear();

        if (el.quizLevelBadge) el.quizLevelBadge.textContent = (quizData.difficulty || "INTERMEDIATE").toUpperCase();
        if (el.quizScoreRatio) el.quizScoreRatio.textContent = `0 / ${(quizData.questions || []).length}`;
        if (el.quizScoreFill) el.quizScoreFill.style.width = "0%";
        if (el.quizFeedbackText) el.quizFeedbackText.textContent = "Select options to verify your spatial & theoretical understanding.";

        if (!el.quizQuestionsList) return;
        el.quizQuestionsList.innerHTML = "";

        const questions = quizData.questions || [];
        questions.forEach((q, qIdx) => {
            const card = document.createElement("div");
            card.className = "question-card";
            card.dataset.qid = q.id || `q_${qIdx}`;

            const targetBadge = q.target_component_id 
                ? `<span class="question-target-badge" data-target="${q.target_component_id}">🎯 Highlight Part: ${q.target_component_id}</span>` 
                : "";

            card.innerHTML = `
                <div class="question-meta-row">
                    <span class="question-type-badge">${(q.type || "mcq").replace("_", " ")}</span>
                    ${targetBadge}
                </div>
                <div class="question-text">${qIdx + 1}. ${q.question}</div>
                <div class="question-options-grid"></div>
                <div class="question-explanation-box" style="display: none;"></div>
            `;

            // Click target badge to highlight component in 3D viewport
            if (q.target_component_id) {
                const badgeEl = card.querySelector(".question-target-badge");
                if (badgeEl) {
                    badgeEl.addEventListener("click", () => {
                        selectComponent(q.target_component_id, false);
                    });
                }
            }

            const optionsGrid = card.querySelector(".question-options-grid");
            const opts = q.options || [];
            opts.forEach((optText, optIdx) => {
                const btn = document.createElement("button");
                btn.className = "quiz-opt-btn";
                btn.textContent = optText;
                btn.addEventListener("click", () => handleQuizOptionClick(q, optIdx, btn, card));
                optionsGrid.appendChild(btn);
            });

            el.quizQuestionsList.appendChild(card);
        });
    }

    function handleQuizOptionClick(question, optIdx, clickedBtn, cardEl) {
        if (quizUserAnswers.has(question.id)) return; // Already answered

        quizUserAnswers.set(question.id, optIdx);
        const isCorrect = (optIdx === question.correct_index);

        const allButtons = cardEl.querySelectorAll(".quiz-opt-btn");
        allButtons.forEach((btn, idx) => {
            btn.disabled = true;
            if (idx === question.correct_index) {
                btn.classList.add(isCorrect ? "selected-correct" : "reveal-correct");
            } else if (idx === optIdx && !isCorrect) {
                btn.classList.add("selected-wrong");
            }
        });

        // Show explanation
        const explBox = cardEl.querySelector(".question-explanation-box");
        if (explBox) {
            explBox.style.display = "block";
            explBox.innerHTML = `<strong>${isCorrect ? "✓ Correct!" : "✗ Incorrect."}</strong> ${question.explanation || ""}`;
            explBox.style.borderLeftColor = isCorrect ? "var(--accent-green)" : "var(--accent-red)";
        }

        // Highlight 3D component if question is linked
        if (question.target_component_id) {
            selectComponent(question.target_component_id, false);
        }

        // Update score
        updateQuizScore();

        // Record single answer to backend student tracker
        fetch("/api/student/record-answer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                topic: (currentQuiz && currentQuiz.topic) || (currentModelSpec && currentModelSpec.topic) || "General Systems",
                question_id: question.id || `q_${optIdx}`,
                student_choice: question.options ? question.options[optIdx] : optIdx,
                correct_index: question.correct_index,
                is_correct: isCorrect,
                question_text: question.question || "",
                explanation: question.explanation || "",
                difficulty: (currentQuiz && currentQuiz.difficulty) || "Intermediate",
            })
        }).then(r => r.json()).then(summary => {
            renderStudentProgress(summary);
        }).catch(err => console.warn("Failed to record student answer:", err));
    }

    function updateQuizScore() {
        if (!currentQuiz || !currentQuiz.questions) return;
        const total = currentQuiz.questions.length;
        let correctCount = 0;
        currentQuiz.questions.forEach(q => {
            if (quizUserAnswers.get(q.id) === q.correct_index) {
                correctCount++;
            }
        });

        const pct = Math.round((correctCount / total) * 100);
        if (el.quizScoreRatio) el.quizScoreRatio.textContent = `${correctCount} / ${total} (${pct}%)`;
        if (el.quizScoreFill) el.quizScoreFill.style.width = `${pct}%`;
        if (el.quizFeedbackText) {
            if (quizUserAnswers.size === total) {
                const missedQuestions = currentQuiz.questions.filter(q => quizUserAnswers.get(q.id) !== q.correct_index);
                let weakCardHtml = "";

                if (missedQuestions.length > 0) {
                    const firstMissed = missedQuestions[0];
                    const compMatch = currentModelSpec && currentModelSpec.components ? currentModelSpec.components.find(c => c.id === firstMissed.target_component_id || (c.name && firstMissed.question && firstMissed.question.toLowerCase().includes(c.name.toLowerCase()))) : null;
                    const weakName = compMatch ? compMatch.name : (firstMissed.target_component_id || "System Core Principle");

                    weakCardHtml = `
                        <div class="weak-concept-card" style="margin-top: 12px; padding: 10px 14px; background: rgba(239, 68, 68, 0.12); border: 1px solid #ef4444; border-radius: 6px; text-align: left;">
                            <div style="font-weight: 600; color: #f87171; font-size: 12px; margin-bottom: 2px;">⚠️ WEAK CONCEPT: ${weakName}</div>
                            <div style="font-size: 11px; color: #cbd5e1; margin-bottom: 8px;">Recommended action: Inspect spatial layout and operational role in the 3D laboratory.</div>
                            <button class="hud-btn hud-btn-accent" id="btn-review-weak-concept" style="font-size: 10px; padding: 4px 10px; cursor: pointer;">🔍 OPEN IN 3D LAB</button>
                        </div>
                    `;
                }

                el.quizFeedbackText.innerHTML = `
                    <div>${pct >= 75 ? `🎉 Excellent! Mastery demonstrated (${pct}%). Ready for Advanced challenges.` : `Quiz complete (${pct}%). Review the Teacher Mode lesson and retry!`}</div>
                    ${weakCardHtml}
                `;

                // Wire up review in 3D button
                setTimeout(() => {
                    const reviewBtn = document.getElementById("btn-review-weak-concept");
                    if (reviewBtn && missedQuestions.length > 0) {
                        reviewBtn.addEventListener("click", () => {
                            if (el.quizModal) el.quizModal.style.display = "none";
                            const firstMissed = missedQuestions[0];
                            const compMatch = currentModelSpec && currentModelSpec.components ? currentModelSpec.components.find(c => c.id === firstMissed.target_component_id || (c.name && firstMissed.question && firstMissed.question.toLowerCase().includes(c.name.toLowerCase()))) : (currentModelSpec && currentModelSpec.components ? currentModelSpec.components[0] : null);
                            if (compMatch) {
                                selectComponent(compMatch.id, true);
                            }
                        });
                    }
                }, 50);

                // Record completed quiz to backend student tracker
                fetch("/api/student/record-quiz", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        topic: (currentQuiz && currentQuiz.topic) || (currentModelSpec && currentModelSpec.topic) || "General Systems",
                        difficulty: (currentQuiz && currentQuiz.difficulty) || "Intermediate",
                        score: correctCount,
                        total_questions: total,
                    })
                }).then(r => r.json()).then(summary => {
                    renderStudentProgress(summary);
                }).catch(err => console.warn("Failed to record quiz completion:", err));
            } else {
                el.quizFeedbackText.textContent = `Answered ${quizUserAnswers.size} of ${total} questions.`;
            }

        }
    }

    async function regenerateQuiz() {
        const spec = currentModelSpec || {
            topic: (el.currentTopicName && el.currentTopicName.textContent) || "Engineering System",
            components: []
        };
        const diff = el.quizDifficultySelect ? el.quizDifficultySelect.value : "Intermediate";
        try {
            if (el.quizLevelBadge) el.quizLevelBadge.textContent = "SYNTHESIZING...";
            if (el.quizFeedbackText) el.quizFeedbackText.textContent = `Synthesizing ${diff} assessment for ${spec.topic}...`;
            if (el.quizQuestionsList && el.quizQuestionsList.children.length === 0) {
                el.quizQuestionsList.innerHTML = `
                    <div style="padding: 24px; text-align: center; color: var(--sec-cyan); font-family: 'Share Tech Mono', monospace; font-size: 12px; letter-spacing: 1px;">
                        <span style="font-size: 24px; display: block; margin-bottom: 8px;">🧪</span>
                        SYNTHESIZING SPATIAL & THEORETICAL QUESTIONS...
                    </div>
                `;
            }
            const resp = await fetch("/api/quiz/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ model_spec: spec, difficulty: diff }),
            });
            if (resp.ok) {
                const quiz = await resp.json();
                renderQuiz(quiz);
            }
        } catch (e) {
            console.error("Regenerate quiz error:", e);
            if (el.quizFeedbackText) el.quizFeedbackText.textContent = `Failed to generate quiz: ${e.message}`;
        }
    }

    function resetQuiz() {
        if (currentQuiz) {
            renderQuiz(currentQuiz);
        }
    }

    async function loadStudentProgress() {
        try {
            const resp = await fetch("/api/student/progress");
            if (!resp.ok) return;
            const data = await resp.json();
            renderStudentProgress(data);
        } catch (e) {
            console.warn("Could not load student progress:", e);
        }
    }

    function renderStudentProgress(data) {
        if (!data) return;
        const tier = data.mastery_tier || "Novice";
        if (el.studentRankBadge) {
            el.studentRankBadge.textContent = tier.toUpperCase();
            el.studentRankBadge.className = "mastery-rank-badge";
            if (tier === "Specialist") el.studentRankBadge.classList.add("specialist");
            else if (tier === "Master Engineer") el.studentRankBadge.classList.add("master-engineer");
        }
        if (el.studentAccuracyVal) el.studentAccuracyVal.textContent = `${data.accuracy_pct || 0.0}%`;
        if (el.studentStreakVal) el.studentStreakVal.textContent = `🔥 ${data.streak || 0}`;
        if (el.studentQuizzesVal) el.studentQuizzesVal.textContent = data.total_quizzes || 0;
        if (el.studentQuestionsVal) el.studentQuestionsVal.textContent = data.total_questions || 0;

        if (el.studentTopicsRow && el.studentMasteredTags) {
            const mastered = data.mastered_topics || [];
            if (mastered.length > 0) {
                el.studentTopicsRow.style.display = "flex";
                el.studentMasteredTags.innerHTML = "";
                mastered.forEach(t => {
                    const tag = document.createElement("span");
                    tag.className = "topic-tag";
                    tag.textContent = `✓ ${t}`;
                    el.studentMasteredTags.appendChild(tag);
                });
            } else {
                el.studentTopicsRow.style.display = "none";
            }
        }
    }

    // ==========================================
    // 4d. SECURE LOCAL OS AGENT
    // ==========================================

    async function executeOsCommand(cmd) {
        if (!cmd) return;
        if (el.osResultBox) el.osResultBox.textContent = `Executing secure command: "${cmd}"...`;

        try {
            const resp = await fetch("/api/os/execute", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ command: cmd, session_id: sessionId }),
            });
            const data = await resp.json();
            renderOsResult(data);
            loadOsStatus();
        } catch (err) {
            if (el.osResultBox) el.osResultBox.textContent = `Error: ${err.message}`;
        }
    }

    function renderOsResult(res) {
        if (!res) return;

        if (res.requires_confirmation) {
            openOsConfirmModal(res.confirmation_id, res.message);
            return;
        }

        if (el.osResultBox) {
            el.osResultBox.textContent = res.message || "Executed safe OS action.";
            el.osResultBox.style.color = res.success ? "var(--sec-cyan)" : "var(--accent-red)";
        }

        // Render processes if list_processes
        if (res.action === "list_processes" && Array.isArray(res.processes)) {
            renderProcessList(res.processes);
        }
    }

    function renderProcessList(procs) {
        if (!el.processTelemetrySection || !el.processTableWrapper) return;
        el.processTelemetrySection.style.display = "block";
        let html = `
            <table class="process-table">
                <thead>
                    <tr><th>PID</th><th>PROCESS</th><th>CPU %</th><th>MEM %</th></tr>
                </thead>
                <tbody>
        `;
        procs.forEach(p => {
            html += `<tr><td>${p.pid}</td><td>${p.name}</td><td>${p.cpu}%</td><td>${p.mem}%</td></tr>`;
        });
        html += `</tbody></table>`;
        el.processTableWrapper.innerHTML = html;
    }

    async function loadOsStatus() {
        try {
            const resp = await fetch("/api/os/status");
            if (!resp.ok) return;
            const data = await resp.json();

            if (el.auditLogContainer && Array.isArray(data.recent_audit_log)) {
                el.auditCountBadge.textContent = `${data.recent_audit_log.length} LOGS`;
                if (data.recent_audit_log.length === 0) {
                    el.auditLogContainer.innerHTML = `<div class="audit-empty">No OS actions recorded in this session.</div>`;
                    return;
                }
                el.auditLogContainer.innerHTML = "";
                data.recent_audit_log.slice().reverse().forEach(entry => {
                    const row = document.createElement("div");
                    row.className = `audit-entry ${entry.status === "REJECTED" ? "rejected" : ""}`;
                    const timeStr = entry.timestamp ? entry.timestamp.split("T")[1]?.slice(0, 8) : "";
                    row.innerHTML = `
                        <div class="audit-entry-top">
                            <span class="audit-entry-action">${entry.action.toUpperCase()}</span>
                            <span>${timeStr} // ${entry.status}</span>
                        </div>
                        <div class="audit-entry-msg">${entry.message || JSON.stringify(entry.params)}</div>
                    `;
                    el.auditLogContainer.appendChild(row);
                });
            }
        } catch (e) {
            console.warn("Could not load OS status:", e);
        }
    }

    function openOsConfirmModal(confirmId, message) {
        pendingConfirmationId = confirmId;
        if (el.confirmModalText) el.confirmModalText.textContent = "Sensitive operating system action authorization:";
        if (el.confirmDetailsBox) el.confirmDetailsBox.textContent = message || "Action requires user approval.";
        if (el.osConfirmModal) el.osConfirmModal.style.display = "flex";
    }

    function closeOsConfirmModal() {
        pendingConfirmationId = null;
        if (el.osConfirmModal) el.osConfirmModal.style.display = "none";
    }

    async function confirmOsAction(approved) {
        if (!pendingConfirmationId) return;
        const cid = pendingConfirmationId;
        closeOsConfirmModal();

        try {
            const resp = await fetch("/api/os/confirm", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ confirmation_id: cid, approved: approved }),
            });
            const data = await resp.json();
            renderOsResult(data);
            loadOsStatus();
        } catch (e) {
            console.error("Confirmation error:", e);
        }
    }

    // ==========================================
    // 4e. VISUAL UNDERSTANDING (IMAGE TO 3D)
    // ==========================================

    let selectedVisionFile = null;

    function openVisionModal() {
        if (el.visionModal) {
            el.visionModal.style.display = "flex";
            if (el.visionPreviewBox) el.visionPreviewBox.style.display = "none";
            if (el.visionDropzone) el.visionDropzone.style.display = "block";
            if (el.visionStatus) el.visionStatus.style.display = "none";
            selectedVisionFile = null;
        }
    }

    function closeVisionModal() {
        if (el.visionModal) el.visionModal.style.display = "none";
        selectedVisionFile = null;
    }

    function handleVisionFileSelect(file) {
        if (!file || !file.type.startsWith("image/")) {
            alert("Please select a valid image file (PNG, JPG, WEBP).");
            return;
        }
        selectedVisionFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            if (el.visionPreviewImg) el.visionPreviewImg.src = e.target.result;
            if (el.visionPreviewBox) el.visionPreviewBox.style.display = "flex";
            if (el.visionDropzone) el.visionDropzone.style.display = "none";
        };
        reader.readAsDataURL(file);
    }

    async function submitVisionTo3D() {
        if (!selectedVisionFile) return;
        const promptHint = el.visionPromptInput ? el.visionPromptInput.value.trim() : "";

        if (el.visionStatus) el.visionStatus.style.display = "flex";
        if (el.visionPreviewBox) el.visionPreviewBox.style.display = "none";

        const formData = new FormData();
        formData.append("file", selectedVisionFile);
        formData.append("instruction", promptHint);
        formData.append("session_id", sessionId);

        try {
            const resp = await fetch("/api/vision/analyze-3d", {
                method: "POST",
                body: formData,
            });
            if (!resp.ok) throw new Error(`Vision synthesis error: ${resp.status}`);
            const data = await resp.json();

            closeVisionModal();

            if (data.model_spec) {
                renderModelSpec(data.model_spec);
                if (data.teacher_lesson) renderTeacherLesson(data.teacher_lesson);
                if (data.quiz) renderQuiz(data.quiz);
                appendChatMessage("AURA", data.text_response || `Reconstructed 3D model from image.`);
                if (isTtsEnabled) speakText(data.text_response || "Reconstructed 3D model from image.");
            }
        } catch (err) {
            alert(`Image-to-3D error: ${err.message}`);
            if (el.visionStatus) el.visionStatus.style.display = "none";
            if (el.visionPreviewBox) el.visionPreviewBox.style.display = "flex";
        }
    }

    // ==========================================
    // 5. UNIFIED AUTONOMOUS AGENT PIPELINE
    // ==========================================

    async function runAgentPipeline(userInstruction) {
        showLoadingOverlay(true);
        updateLoadingProgress("AGENT PLANNING", "Classifying intent & decomposing learning task...", 1);
        setPipelineStatus("PLANNING & ROUTING", true);

        try {
            setTimeout(() => updateLoadingProgress("SCHEMATICS & KNOWLEDGE", "Searching web references & technical schematics...", 2), 600);
            setTimeout(() => updateLoadingProgress("DYNAMIC 3D SYNTHESIS", "Synthesizing 3D ModelSpec with Google Gemini AI...", 3), 1300);

            const resp = await fetch("/api/agent/run", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_instruction: userInstruction,
                    session_id: sessionId,
                }),
            });

            if (!resp.ok) {
                throw new Error(`Agent run error: ${resp.status}`);
            }

            updateLoadingProgress("8D VERIFICATION", "Validating geometric bounds, conduits & animations...", 4);
            const data = await resp.json();

            updateLoadingProgress("SCENE UPDATE", "Updating Three.js WebGL viewport & pedagogy...", 5);

            setTimeout(() => {
                showLoadingOverlay(false);

                // If a 3D model is generated or updated
                if (data.model_spec) {
                    renderModelSpec(data.model_spec);
                }

                // If real reference images found
                if (data.reference_images) {
                    renderReferenceGallery(data.reference_images, data.model_spec?.topic);
                }

                // If teacher lesson synthesized
                if (data.teacher_lesson) {
                    renderTeacherLesson(data.teacher_lesson);
                }

                // If quiz synthesized
                if (data.quiz) {
                    renderQuiz(data.quiz);
                }

                // If OS command result
                if (data.os_result) {
                    renderOsResult(data.os_result);
                }

                // Switch tabs automatically based on intent
                if (data.intent === "TEACHER_EXPLAIN") {
                    switchRightPanelTab("teacher");
                } else if (data.intent === "GENERATE_QUIZ") {
                    switchRightPanelTab("quiz");
                } else if (data.intent === "OS_AUTOMATION") {
                    switchRightPanelTab("os");
                }

                // Chat response delivery
                const textReply = data.text_response || "Action executed successfully.";
                appendChatMessage("AURA", textReply);
                if (isTtsEnabled) speakText(textReply);

                // Pipeline Status Badge
                const vScore = data.verification_report?.score || 100;
                setPipelineStatus(`VERIFIED // SCORE: ${vScore}%`, false);

            }, 400);

        } catch (err) {
            console.error("Agentic pipeline failure:", err);
            showLoadingOverlay(false);
            setPipelineStatus("AGENT ERROR", false);
            appendChatMessage("AURA", `Agent execution error: ${err.message}. Running fallback...`);
            // Fallback direct generation
            await requestModelGeneration(userInstruction);
        }
    }

    function setPipelineStatus(statusText, isActive) {
        if (el.pipelineStatusText) el.pipelineStatusText.textContent = `PIPELINE: ${statusText}`;
        if (el.pipelineStatusChip) el.pipelineStatusChip.classList.toggle("active", isActive);
    }

    async function requestModelGeneration(promptText, forceCatalog = false) {
        showLoadingOverlay(true);
        updateLoadingProgress("UNDERSTANDING REQUEST", "Analyzing scientific intent & physical principles...", 1);

        try {
            setTimeout(() => updateLoadingProgress("IDENTIFYING COMPONENTS", "Formulating structural assembly & joints...", 2), 600);
            setTimeout(() => updateLoadingProgress("PLANNING 3D STRUCTURE", "Calculating 3D coordinates & conduits...", 3), 1200);

            const resp = await fetch("/api/model/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ prompt: promptText, force_catalog: forceCatalog }),
            });

            if (!resp.ok) {
                throw new Error(`Generation error: ${resp.status}`);
            }

            updateLoadingProgress("VALIDATING MODEL", "Verifying ModelSpec schema & repairing geometry...", 4);
            const spec = await resp.json();

            updateLoadingProgress("BUILDING 3D SCENE", "Initializing WebGL shaders & leader lines...", 5);
            setTimeout(() => {
                renderModelSpec(spec);
                showLoadingOverlay(false);
                appendChatMessage("AURA", `Constructed 3D model for **${spec.topic}**. ${spec.explanation}`);
                if (isTtsEnabled) speakText(`Constructed 3D model for ${spec.topic}.`);
            }, 500);

        } catch (err) {
            console.error("Failed to generate model:", err);
            showLoadingOverlay(false);
            appendChatMessage("AURA", `Could not generate 3D model: ${err.message}. Please check your connection.`);
        }
    }

    function showLoadingOverlay(show) {
        el.generationOverlay.style.display = show ? "flex" : "none";
    }

    function updateLoadingProgress(title, subtitle, stepNum) {
        el.stageTitle.textContent = title;
        el.stageSubtitle.textContent = subtitle;
        for (let i = 1; i <= 5; i++) {
            const stepEl = document.getElementById(`step-${i}`);
            if (stepEl) stepEl.classList.toggle("active", i <= stepNum);
        }
    }

    // ==========================================
    // 6. NATURAL LANGUAGE & VOICE PARSER
    // ==========================================

    function initVoiceRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            el.voiceInputBtn.style.opacity = "0.5";
            el.voiceInputBtn.title = "Voice recognition not supported in this browser.";
            return;
        }

        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = "en-US";

        recognition.onstart = () => {
            isListening = true;
            el.voiceInputBtn.classList.add("recording");
            el.micIcon.textContent = "🔴";
        };

        recognition.onend = () => {
            isListening = false;
            el.voiceInputBtn.classList.remove("recording");
            el.micIcon.textContent = "🎤";
        };

        recognition.onresult = async (event) => {
            const transcript = event.results[0][0].transcript.trim();
            if (transcript) {
                el.mainPromptInput.value = transcript;
                await processUserPrompt(transcript);
            }
        };

        recognition.onerror = (event) => {
            console.warn("Speech recognition error:", event.error);
            isListening = false;
            el.voiceInputBtn.classList.remove("recording");
            el.micIcon.textContent = "🎤";
        };
    }

    function toggleVoiceInput() {
        if (!recognition) {
            alert("Voice input is not supported in this browser. You can type instructions directly!");
            return;
        }
        if (isListening) {
            recognition.stop();
        } else {
            recognition.start();
        }
    }

    function speakText(text) {
        if (!window.speechSynthesis || !isTtsEnabled) return;
        window.speechSynthesis.cancel();
        const clean = text.replace(/[*_#`]/g, "");
        const utterance = new SpeechSynthesisUtterance(clean);
        utterance.rate = 1.05;
        utterance.pitch = 1.0;
        window.speechSynthesis.speak(utterance);
    }

    async function processUserPrompt(rawText) {
        const text = rawText.trim();
        if (!text) return;

        appendChatMessage("You", text);
        el.mainPromptInput.value = "";

        // Check if user is asking for rapid local viewport or animation controls
        try {
            const compMap = {};
            if (currentModelSpec && currentModelSpec.components) {
                currentModelSpec.components.forEach(c => {
                    compMap[c.id] = { name: c.name, description: c.description };
                });
            }

            const parseResp = await fetch("/api/voice/parse", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: text, component_map: compMap }),
            });
            const parsed = await parseResp.json();

            // Handle immediate local viewport/playback actions
            if (parsed.intent === "animation") {
                const act = parsed.action;
                if (act === "play") playAnimation();
                else if (act === "pause") pauseAnimation();
                else if (act === "next") nextAnimStep();
                else if (act === "previous") prevAnimStep();
                else if (act === "reset") resetAnimation();
                appendChatMessage("AURA", `Animation command executed: **${act}**`);
                return;
            }

            if (parsed.intent === "select_component" && parsed.component_id) {
                selectComponent(parsed.component_id, true);
                appendChatMessage("AURA", `Inspecting component: **${parsed.component_id}**`);
                return;
            }

            if (parsed.intent === "gesture") {
                const act = parsed.action;
                if (act === "toggle_gestures") {
                    toggleWebcamGestures();
                    const stateMsg = isGestureActive ? "ACTIVATED" : "DEACTIVATED";
                    appendChatMessage("AURA", `Webcam hand gestures **${stateMsg}**. Move your hand in front of the camera to rotate the 3D model, pinch to zoom, and form a fist to reset.`);
                    if (isTtsEnabled) speakText(isGestureActive ? "Webcam hand gestures activated." : "Webcam gestures stopped.");
                    return;
                }
                if (act === "rotate") rotateCamera(Math.PI / 4);
                else if (act === "zoom_in") zoomCamera(-1.5);
                else if (act === "zoom_out") zoomCamera(1.5);
                else if (act === "reset") resetCameraView();
                appendChatMessage("AURA", `Viewport adjusted: **${act}**`);
                return;
            }

            if (parsed.intent === "generate_quiz" || text.toLowerCase().includes("quiz")) {
                switchRightPanelTab("quiz");
                if (!currentQuiz || !el.quizQuestionsList || el.quizQuestionsList.children.length === 0) {
                    await regenerateQuiz();
                }
                appendChatMessage("AURA", `Interactive quiz ready for **${currentModelSpec?.topic || "this topic"}**. Choose the best options in the Quiz Lab panel to test your knowledge!`);
                if (isTtsEnabled) speakText("Interactive quiz ready in the Quiz Lab.");
                return;
            }

            // For dynamic generation, modifications, semantic physics animations, 
            // teacher pedagogy, quizzes, OS automation, and conversational learning:
            await runAgentPipeline(text);

        } catch (err) {
            console.error("Failed to process command with agent pipeline:", err);
            await runAgentPipeline(text);
        }
    }

    async function sendContextualChat(userMessage) {
        try {
            const chatPayload = {
                messages: [{ role: "user", content: userMessage }],
                document_context: documentContext,
                current_model_context: currentModelSpec,
            };

            const resp = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(chatPayload),
            });

            if (!resp.ok) throw new Error(`Chat error: ${resp.status}`);
            const data = await resp.json();
            appendChatMessage("AURA", data.response);
            if (isTtsEnabled) speakText(data.response);
        } catch (err) {
            appendChatMessage("AURA", `Chat error: ${err.message}`);
        }
    }

    function appendChatMessage(sender, text) {
        const msg = document.createElement("div");
        msg.className = `message ${sender.toLowerCase() === "you" ? "user" : "assistant"}`;
        msg.innerHTML = `
            <div class="sender">${sender.toUpperCase()}</div>
            <div class="text">${text}</div>
        `;
        el.chatMessages.appendChild(msg);
        el.chatMessages.scrollTop = el.chatMessages.scrollHeight;
    }

    // ==========================================
    // 6b. REAL-TIME WEBCAM HAND GESTURE 3D CONTROLLER
    // ==========================================

    const HAND_CONNECTIONS = [
        [0, 1], [1, 2], [2, 3], [3, 4],        // Thumb
        [0, 5], [5, 6], [6, 7], [7, 8],        // Index
        [5, 9], [9, 10], [10, 11], [11, 12],   // Middle
        [9, 13], [13, 14], [14, 15], [15, 16], // Ring
        [13, 17], [17, 18], [18, 19], [19, 20],// Pinky
        [0, 17]                                // Palm base
    ];

    async function toggleWebcamGestures() {
        if (isGestureActive) {
            stopWebcamGestures();
        } else {
            await startWebcamGestures();
        }
    }

    async function startWebcamGestures() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            alert("Webcam access is not supported by your browser or connection.");
            return;
        }

        try {
            isGestureActive = true;
            if (el.btnHeaderGestures) el.btnHeaderGestures.classList.add("active");
            if (el.gesturePip) el.gesturePip.style.display = "flex";
            if (el.gestureStatusBadge) el.gestureStatusBadge.textContent = "INITIALIZING...";

            const stream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 320 }, height: { ideal: 240 }, facingMode: "user" },
                audio: false
            });

            gestureStream = stream;
            if (el.gestureVideo) {
                el.gestureVideo.srcObject = stream;
                await el.gestureVideo.play();
            }

            if (el.gestureStatusBadge) el.gestureStatusBadge.textContent = "TRACKING ACTIVE";

            // If MediaPipe Hands is loaded from CDN, use high-precision landmark detector
            if (typeof window.Hands !== "undefined") {
                initMediaPipeTracking();
            } else {
                // High-speed Canvas Computer Vision fallback
                initCanvasVisionTracking();
            }

        } catch (err) {
            console.error("Webcam gesture start error:", err);
            isGestureActive = false;
            if (el.btnHeaderGestures) el.btnHeaderGestures.classList.remove("active");
            if (el.gestureStatusBadge) el.gestureStatusBadge.textContent = "CAM BLOCKED";
            setTimeout(() => {
                if (el.gesturePip) el.gesturePip.style.display = "none";
            }, 3000);
        }
    }

    function stopWebcamGestures() {
        isGestureActive = false;
        if (el.btnHeaderGestures) el.btnHeaderGestures.classList.remove("active");
        if (el.gesturePip) el.gesturePip.style.display = "none";

        if (gestureStream) {
            gestureStream.getTracks().forEach(t => t.stop());
            gestureStream = null;
        }
        if (mpCamera && typeof mpCamera.stop === "function") {
            try { mpCamera.stop(); } catch (e) {}
            mpCamera = null;
        }
        if (gestureAnimFrameId) {
            cancelAnimationFrame(gestureAnimFrameId);
            gestureAnimFrameId = null;
        }
        if (el.gestureVideo) {
            el.gestureVideo.srcObject = null;
        }
        if (el.gestureCanvas) {
            const ctx = el.gestureCanvas.getContext("2d");
            if (ctx) ctx.clearRect(0, 0, el.gestureCanvas.width, el.gestureCanvas.height);
        }
        lastHandPos = null;
        lastHandPinchDist = null;
        lastHandArea = null;
    }

    function initMediaPipeTracking() {
        try {
            mpHands = new window.Hands({
                locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`
            });

            mpHands.setOptions({
                maxNumHands: 1,
                modelComplexity: 0,
                minDetectionConfidence: 0.5,
                minTrackingConfidence: 0.5
            });

            mpHands.onResults(onMediaPipeResults);

            if (typeof window.Camera !== "undefined") {
                mpCamera = new window.Camera(el.gestureVideo, {
                    onFrame: async () => {
                        if (isGestureActive && mpHands && el.gestureVideo.readyState >= 2) {
                            await mpHands.send({ image: el.gestureVideo });
                        }
                    },
                    width: 320,
                    height: 240
                });
                mpCamera.start();
            } else {
                const processFrame = async () => {
                    if (!isGestureActive) return;
                    if (el.gestureVideo && el.gestureVideo.readyState >= 2 && mpHands) {
                        try {
                            await mpHands.send({ image: el.gestureVideo });
                        } catch (e) {}
                    }
                    gestureAnimFrameId = requestAnimationFrame(processFrame);
                };
                gestureAnimFrameId = requestAnimationFrame(processFrame);
            }
        } catch (e) {
            console.warn("Failed to initialize MediaPipe tracking, falling back to Canvas CV:", e);
            initCanvasVisionTracking();
        }
    }

    function onMediaPipeResults(results) {
        if (!isGestureActive || !el.gestureCanvas) return;
        const canvas = el.gestureCanvas;
        const ctx = canvas.getContext("2d");
        const w = (canvas.width = el.gestureVideo.videoWidth || 320);
        const h = (canvas.height = el.gestureVideo.videoHeight || 240);

        ctx.clearRect(0, 0, w, h);

        if (!results.multiHandLandmarks || results.multiHandLandmarks.length === 0) {
            if (el.gestureStatusBadge) el.gestureStatusBadge.textContent = "SEARCHING FOR HAND";
            lastHandPos = null;
            lastHandPinchDist = null;
            return;
        }

        const lm = results.multiHandLandmarks[0];

        // Draw Skeleton Lines (HUD Cyan)
        ctx.strokeStyle = "rgba(0, 212, 255, 0.7)";
        ctx.lineWidth = 2;
        HAND_CONNECTIONS.forEach(([i, j]) => {
            ctx.beginPath();
            ctx.moveTo(lm[i].x * w, lm[i].y * h);
            ctx.lineTo(lm[j].x * w, lm[j].y * h);
            ctx.stroke();
        });

        // Draw Joint Points (HUD Green/Cyan)
        lm.forEach((pt, idx) => {
            ctx.beginPath();
            ctx.arc(pt.x * w, pt.y * h, (idx === 8 || idx === 4) ? 5 : 3, 0, Math.PI * 2);
            ctx.fillStyle = (idx === 8 || idx === 4) ? "#ff8c00" : "#39ff14";
            ctx.fill();
        });

        const now = Date.now();

        // 1. Check Pinch (Thumb 4 & Index 8)
        const pinchDist = Math.hypot(lm[4].x - lm[8].x, lm[4].y - lm[8].y);
        const isPinch = pinchDist < 0.075;

        // 2. Check Fist (Tips 8, 12, 16, 20 close to wrist 0)
        const d8 = Math.hypot(lm[8].x - lm[0].x, lm[8].y - lm[0].y);
        const d12 = Math.hypot(lm[12].x - lm[0].x, lm[12].y - lm[0].y);
        const d16 = Math.hypot(lm[16].x - lm[0].x, lm[16].y - lm[0].y);
        const d20 = Math.hypot(lm[20].x - lm[0].x, lm[20].y - lm[0].y);
        const isFist = (d8 < 0.28 && d12 < 0.28 && d16 < 0.28 && d20 < 0.28);

        if (isFist) {
            if (el.gestureStatusBadge) el.gestureStatusBadge.textContent = "FIST // RESET VIEW";
            drawGestureHUD(ctx, "✊ FIST: RESET VIEW", lm[0].x * w, lm[0].y * h);
            if (now - lastGestureActionTime > 800) {
                resetCameraView();
                lastGestureActionTime = now;
            }
            lastHandPos = null;
            return;
        }

        if (isPinch) {
            if (el.gestureStatusBadge) el.gestureStatusBadge.textContent = "PINCH // ZOOMING";
            drawGestureHUD(ctx, "👌 PINCH: ZOOM", lm[8].x * w, lm[8].y * h);
            if (lastHandPos) {
                const dy = lm[8].y - lastHandPos.y;
                if (Math.abs(dy) > 0.005) {
                    zoomCameraByDelta(dy * 16.0);
                }
            }
            lastHandPos = { x: lm[8].x, y: lm[8].y };
            return;
        }

        // 3. Normal Pointing / Hand Move: Rotate Model
        const curX = lm[8].x;
        const curY = lm[8].y;
        if (el.gestureStatusBadge) el.gestureStatusBadge.textContent = "TRACKING // ROTATE";
        drawGestureHUD(ctx, "☝️ ROTATE 3D", curX * w, curY * h);

        if (lastHandPos) {
            const dx = curX - lastHandPos.x;
            const dy = curY - lastHandPos.y;
            if (Math.abs(dx) > 0.003 || Math.abs(dy) > 0.003) {
                orbitCameraByDelta(dx, dy);
            }
        }
        lastHandPos = { x: curX, y: curY };
    }

    // High-speed Canvas Computer Vision fallback (works 100% offline & without CDN)
    function initCanvasVisionTracking() {
        const offCanvas = document.createElement("canvas");
        offCanvas.width = 160;
        offCanvas.height = 120;
        const offCtx = offCanvas.getContext("2d", { willReadFrequently: true });

        const processCvFrame = () => {
            if (!isGestureActive) return;
            if (el.gestureVideo && el.gestureVideo.readyState >= 2 && el.gestureCanvas) {
                const canvas = el.gestureCanvas;
                const ctx = canvas.getContext("2d");
                const w = (canvas.width = el.gestureVideo.videoWidth || 320);
                const h = (canvas.height = el.gestureVideo.videoHeight || 240);

                ctx.clearRect(0, 0, w, h);
                offCtx.drawImage(el.gestureVideo, 0, 0, 160, 120);

                const frame = offCtx.getImageData(0, 0, 160, 120);
                const data = frame.data;
                let sumX = 0;
                let sumY = 0;
                let skinPixels = 0;

                for (let i = 0; i < data.length; i += 8) {
                    const r = data[i];
                    const g = data[i + 1];
                    const b = data[i + 2];
                    // Fast skin-tone heuristic
                    if (r > 60 && g > 40 && b > 20 && r > g && r > b && (r - g) > 12) {
                        const pxIdx = i / 4;
                        const x = pxIdx % 160;
                        const y = Math.floor(pxIdx / 160);
                        sumX += x;
                        sumY += y;
                        skinPixels++;
                    }
                }

                if (skinPixels > 120) {
                    const normX = (sumX / skinPixels) / 160;
                    const normY = (sumY / skinPixels) / 120;
                    const screenX = normX * w;
                    const screenY = normY * h;

                    // Draw tracking reticle & crosshair
                    ctx.strokeStyle = "#00d4ff";
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    ctx.arc(screenX, screenY, 20, 0, Math.PI * 2);
                    ctx.stroke();

                    ctx.strokeStyle = "rgba(57, 255, 20, 0.6)";
                    ctx.beginPath();
                    ctx.moveTo(screenX - 28, screenY);
                    ctx.lineTo(screenX + 28, screenY);
                    ctx.moveTo(screenX, screenY - 28);
                    ctx.lineTo(screenX, screenY + 28);
                    ctx.stroke();

                    const now = Date.now();

                    // Check area change for zoom
                    if (lastHandArea !== null) {
                        const areaDiff = skinPixels - lastHandArea;
                        if (Math.abs(areaDiff) > 180 && now - lastGestureActionTime > 150) {
                            zoomCameraByDelta(areaDiff > 0 ? -1.0 : 1.0);
                            lastGestureActionTime = now;
                            if (el.gestureStatusBadge) el.gestureStatusBadge.textContent = "CV // ZOOM";
                            drawGestureHUD(ctx, "🔍 ZOOM", screenX, screenY);
                        }
                    }
                    lastHandArea = skinPixels;

                    // Track movement to orbit 3D model
                    if (lastHandPos) {
                        const dx = normX - lastHandPos.x;
                        const dy = normY - lastHandPos.y;
                        if (Math.abs(dx) > 0.005 || Math.abs(dy) > 0.005) {
                            orbitCameraByDelta(dx, dy);
                            if (el.gestureStatusBadge) el.gestureStatusBadge.textContent = "CV // ROTATE";
                            drawGestureHUD(ctx, "☝️ ROTATE", screenX, screenY);
                        }
                    }
                    lastHandPos = { x: normX, y: normY };

                } else {
                    if (el.gestureStatusBadge) el.gestureStatusBadge.textContent = "SEARCHING FOR HAND";
                    lastHandPos = null;
                    lastHandArea = null;
                }
            }
            gestureAnimFrameId = requestAnimationFrame(processCvFrame);
        };
        gestureAnimFrameId = requestAnimationFrame(processCvFrame);
    }

    function drawGestureHUD(ctx, label, x, y) {
        ctx.save();
        ctx.font = "bold 11px 'Share Tech Mono', monospace";
        ctx.fillStyle = "#ff8c00";
        ctx.shadowColor = "rgba(0, 0, 0, 0.9)";
        ctx.shadowBlur = 4;
        ctx.fillText(label, Math.max(10, Math.min(x - 20, ctx.canvas.width - 120)), Math.max(20, y - 15));
        ctx.restore();
    }

    // ==========================================
    // 7. STUDY MATERIAL READING EXTRACTOR
    // ==========================================

    async function handleFileUpload(file) {
        if (!file) return;
        el.uploadStatus.style.display = "flex";
        el.uploadStatusText.textContent = `Analyzing ${file.name}...`;

        const formData = new FormData();
        formData.append("file", file);

        try {
            const resp = await fetch("/api/reading/extract", {
                method: "POST",
                body: formData,
            });

            if (!resp.ok) {
                const errData = await resp.json();
                throw new Error(errData.detail || "Failed to extract reading");
            }

            const data = await resp.json();
            documentContext = data.full_text;

            // Render topics in right panel
            el.topicsSection.style.display = "flex";
            el.topicsList.innerHTML = "";
            (data.topics || []).forEach(t => {
                const btn = document.createElement("button");
                btn.className = "topic-btn";
                btn.textContent = `◈ ${t.topic}`;
                btn.addEventListener("click", () => {
                    requestModelGeneration(`Create a 3D educational model visualizing ${t.topic}`);
                });
                el.topicsList.appendChild(btn);
            });

            el.uploadStatus.style.display = "none";
            el.uploadModal.style.display = "none";

            appendChatMessage("AURA", `Loaded study material **${file.name}** (${data.char_count.toLocaleString()} characters). Identified ${data.topics.length} key 3D topics. Select a topic in the right panel or ask any question.`);

            // Automatically build model for top topic if available
            if (data.topics && data.topics.length > 0) {
                requestModelGeneration(`Create a 3D educational model visualizing ${data.topics[0].topic}`);
            }

        } catch (err) {
            el.uploadStatusText.textContent = `Error: ${err.message}`;
            setTimeout(() => { el.uploadStatus.style.display = "none"; }, 3000);
        }
    }

    // ==========================================
    // 8. EXAMPLES EXPLORER MODAL
    // ==========================================

    async function loadExamplesLibrary() {
        try {
            const resp = await fetch("/api/examples");
            const data = await resp.json();
            renderExamplesModal(data.categories || {});
        } catch (err) {
            console.error("Failed to load examples library:", err);
        }
    }

    function renderExamplesModal(categories) {
        el.categoryTabs.innerHTML = "";
        el.examplesCardsGrid.innerHTML = "";

        const allTab = document.createElement("button");
        allTab.className = "cat-tab active";
        allTab.textContent = "ALL MODELS";
        el.categoryTabs.appendChild(allTab);

        const allExamples = [];

        Object.keys(categories).forEach(cat => {
            const tab = document.createElement("button");
            tab.className = "cat-tab";
            tab.textContent = cat.toUpperCase();
            tab.addEventListener("click", () => {
                document.querySelectorAll(".cat-tab").forEach(t => t.classList.remove("active"));
                tab.classList.add("active");
                filterCards(cat);
            });
            el.categoryTabs.appendChild(tab);

            categories[cat].forEach(ex => {
                ex.category = cat;
                allExamples.push(ex);
            });
        });

        allTab.addEventListener("click", () => {
            document.querySelectorAll(".cat-tab").forEach(t => t.classList.remove("active"));
            allTab.classList.add("active");
            filterCards("ALL");
        });

        function filterCards(selectedCat) {
            el.examplesCardsGrid.innerHTML = "";
            const search = el.examplesSearchInput.value.toLowerCase();
            const filtered = allExamples.filter(ex => {
                const matchCat = (selectedCat === "ALL" || ex.category === selectedCat);
                const matchSearch = ex.title.toLowerCase().includes(search) || ex.description.toLowerCase().includes(search);
                return matchCat && matchSearch;
            });

            filtered.forEach(ex => {
                const card = document.createElement("div");
                card.className = "ex-card";
                card.innerHTML = `
                    <div class="ex-card-title">${ex.title}</div>
                    <div class="ex-card-desc">${ex.description}</div>
                    <div class="ex-card-footer">
                        <span class="diff-badge diff-${ex.difficulty}">${ex.difficulty}</span>
                        <span class="hud-btn hud-btn-accent" style="padding: 2px 8px; font-size: 10px;">BUILD ➔</span>
                    </div>
                `;
                card.addEventListener("click", () => {
                    el.examplesModal.style.display = "none";
                    requestModelGeneration(ex.prompt);
                });
                el.examplesCardsGrid.appendChild(card);
            });
        }

        el.examplesSearchInput.addEventListener("input", () => {
            const activeTab = document.querySelector(".cat-tab.active");
            const cat = activeTab ? activeTab.textContent : "ALL";
            filterCards(cat === "ALL MODELS" ? "ALL" : cat);
        });

        filterCards("ALL");
    }

    // ==========================================
    // 9. TELEMETRY POLLING
    // ==========================================

    async function pollTelemetry() {
        try {
            const resp = await fetch("/api/telemetry");
            if (resp.ok) {
                const data = await resp.json();
                el.telemetryCpu.textContent = `${data.cpu_percent}%`;
                el.telemetryCpuBar.style.width = `${data.cpu_percent}%`;
                el.telemetryRam.textContent = `${data.ram_percent}%`;
                el.telemetryRamBar.style.width = `${data.ram_percent}%`;
            }
        } catch (err) {
            // Silently ignore telemetry poll errors
        }
    }

    // ==========================================
    // 10. EVENT LISTENERS & BOOTSTRAP
    // ==========================================

    function setupEventListeners() {
        // Animation Bar Buttons
        el.animPlayPause.addEventListener("click", () => {
            if (isPlayingAnim) pauseAnimation();
            else playAnimation();
        });
        el.animNext.addEventListener("click", nextAnimStep);
        el.animPrev.addEventListener("click", prevAnimStep);
        el.animReset.addEventListener("click", resetAnimation);
        el.animTourBtn.addEventListener("click", startPartsTour);

        // Inspector Buttons
        el.compSpeakBtn.addEventListener("click", () => {
            if (selectedComponentId && currentModelSpec) {
                const comp = currentModelSpec.components.find(c => c.id === selectedComponentId);
                if (comp) speakText(`${comp.name}. ${comp.description}`);
            }
        });
        el.compAskBtn.addEventListener("click", () => {
            if (selectedComponentId && currentModelSpec) {
                const comp = currentModelSpec.components.find(c => c.id === selectedComponentId);
                if (comp) {
                    const promptText = `Explain the engineering function of the ${comp.name} in detail.`;
                    el.mainPromptInput.value = promptText;
                    processUserPrompt(promptText);
                }
            }
        });


        // Left Panel Buttons
        document.getElementById("quick-create-btn").addEventListener("click", () => {
            el.mainPromptInput.value = "Create a 3D model of ";
            el.mainPromptInput.focus();
        });
        document.getElementById("quick-tour-btn").addEventListener("click", startPartsTour);
        document.getElementById("quick-labels-btn").addEventListener("click", () => {
            showLabels = !showLabels;
            labelSprites.forEach(s => s.visible = showLabels);
        });

        // Chat & Prompt Input
        el.sendPromptBtn.addEventListener("click", () => processUserPrompt(el.mainPromptInput.value));
        el.mainPromptInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") processUserPrompt(el.mainPromptInput.value);
        });

        // Voice Controls
        el.voiceInputBtn.addEventListener("click", toggleVoiceInput);
        el.btnVoiceToggle.addEventListener("click", () => {
            isTtsEnabled = !isTtsEnabled;
            el.ttsIcon.textContent = isTtsEnabled ? "🔊" : "🔇";
            el.btnVoiceToggle.textContent = isTtsEnabled ? "AUDIO ON" : "AUDIO MUTED";
            if (!isTtsEnabled && window.speechSynthesis) window.speechSynthesis.cancel();
        });

        // Modals
        el.btnOpenExamples.addEventListener("click", () => {
            el.examplesModal.style.display = "flex";
        });
        el.examplesCloseBtn.addEventListener("click", () => {
            el.examplesModal.style.display = "none";
        });

        el.btnUploadTrigger.addEventListener("click", () => {
            el.uploadModal.style.display = "flex";
        });
        el.uploadCloseBtn.addEventListener("click", () => {
            el.uploadModal.style.display = "none";
        });
        el.fileUploadBtn.addEventListener("click", () => el.hiddenFileInput.click());
        el.browseFilesBtn.addEventListener("click", () => el.hiddenFileInput.click());

        el.hiddenFileInput.addEventListener("change", (e) => {
            if (e.target.files.length > 0) handleFileUpload(e.target.files[0]);
        });

        // Dropzone drag-and-drop
        el.uploadDropzone.addEventListener("dragover", (e) => {
            e.preventDefault();
            el.uploadDropzone.classList.add("dragover");
        });
        el.uploadDropzone.addEventListener("dragleave", () => {
            el.uploadDropzone.classList.remove("dragover");
        });
        el.uploadDropzone.addEventListener("drop", (e) => {
            e.preventDefault();
            el.uploadDropzone.classList.remove("dragover");
            if (e.dataTransfer.files.length > 0) handleFileUpload(e.dataTransfer.files[0]);
        });

        // Chat Drawer Toggle
        document.getElementById("chat-toggle-btn").addEventListener("click", () => {
            const drawer = document.getElementById("chat-drawer");
            drawer.classList.toggle("collapsed");
            document.getElementById("chat-toggle-btn").textContent = drawer.classList.contains("collapsed") ? "▲" : "▼";
        });

        // Header Quick Action Buttons
        if (el.btnHeaderTeacher) {
            el.btnHeaderTeacher.addEventListener("click", () => switchRightPanelTab("teacher"));
        }
        if (el.btnHeaderQuiz) {
            el.btnHeaderQuiz.addEventListener("click", () => switchRightPanelTab("quiz"));
        }
        if (el.btnHeaderGestures) {
            el.btnHeaderGestures.addEventListener("click", toggleWebcamGestures);
        }
        if (el.gesturePipClose) {
            el.gesturePipClose.addEventListener("click", stopWebcamGestures);
        }
        if (el.btnHeaderVision) {
            el.btnHeaderVision.addEventListener("click", openVisionModal);
        }
        if (el.headerOsStatus) {
            el.headerOsStatus.addEventListener("click", () => switchRightPanelTab("os"));
        }

        // Right Panel 5-Tab Switcher
        if (el.tabBtnInspector) {
            el.tabBtnInspector.addEventListener("click", () => switchRightPanelTab("inspector"));
        }
        if (el.tabBtnReferences) {
            el.tabBtnReferences.addEventListener("click", () => switchRightPanelTab("references"));
        }
        if (el.tabBtnTeacher) {
            el.tabBtnTeacher.addEventListener("click", () => switchRightPanelTab("teacher"));
        }
        if (el.tabBtnQuiz) {
            el.tabBtnQuiz.addEventListener("click", () => switchRightPanelTab("quiz"));
        }
        if (el.tabBtnOs) {
            el.tabBtnOs.addEventListener("click", () => switchRightPanelTab("os"));
        }

        // AI Teacher Mode Controls
        if (el.teacherReadBtn) {
            el.teacherReadBtn.addEventListener("click", speakTeacherLesson);
        }
        if (el.teacherGenerateBtn) {
            el.teacherGenerateBtn.addEventListener("click", refreshTeacherLesson);
        }
        if (el.teacherLevelSelect) {
            el.teacherLevelSelect.addEventListener("change", refreshTeacherLesson);
        }


        // Quiz Lab Controls
        if (el.btnRegenQuiz) {
            el.btnRegenQuiz.addEventListener("click", regenerateQuiz);
        }
        if (el.quizResetBtn) {
            el.quizResetBtn.addEventListener("click", resetQuiz);
        }

        // Secure OS Agent Controls & Launchpad
        document.querySelectorAll(".os-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const cmd = btn.dataset.cmd;
                if (cmd) executeOsCommand(cmd);
            });
        });
        if (el.btnExecOs) {
            el.btnExecOs.addEventListener("click", () => {
                const cmd = el.osCustomInput ? el.osCustomInput.value.trim() : "";
                if (cmd) executeOsCommand(cmd);
            });
        }
        if (el.osCustomInput) {
            el.osCustomInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter") {
                    const cmd = el.osCustomInput.value.trim();
                    if (cmd) executeOsCommand(cmd);
                }
            });
        }

        // OS Action Confirmation Modal
        if (el.btnConfirmYes) {
            el.btnConfirmYes.addEventListener("click", () => confirmOsAction(true));
        }
        if (el.btnConfirmNo) {
            el.btnConfirmNo.addEventListener("click", () => confirmOsAction(false));
        }
        if (el.confirmCloseBtn) {
            el.confirmCloseBtn.addEventListener("click", closeOsConfirmModal);
        }

        // Vision Modal (Image to 3D Reconstructor)
        if (el.visionCloseBtn) {
            el.visionCloseBtn.addEventListener("click", closeVisionModal);
        }
        if (el.visionBrowseBtn && el.visionFileInput) {
            el.visionBrowseBtn.addEventListener("click", () => el.visionFileInput.click());
        }
        if (el.visionFileInput) {
            el.visionFileInput.addEventListener("change", (e) => {
                if (e.target.files.length > 0) handleVisionFileSelect(e.target.files[0]);
            });
        }
        if (el.visionDropzone) {
            el.visionDropzone.addEventListener("dragover", (e) => {
                e.preventDefault();
                el.visionDropzone.classList.add("dragover");
            });
            el.visionDropzone.addEventListener("dragleave", () => {
                el.visionDropzone.classList.remove("dragover");
            });
            el.visionDropzone.addEventListener("drop", (e) => {
                e.preventDefault();
                el.visionDropzone.classList.remove("dragover");
                if (e.dataTransfer.files.length > 0) handleVisionFileSelect(e.dataTransfer.files[0]);
            });
        }
        if (el.visionSubmitBtn) {
            el.visionSubmitBtn.addEventListener("click", submitVisionTo3D);
        }

        // Reference Image Lightbox Modal
        if (el.lightboxCloseBtn) {
            el.lightboxCloseBtn.addEventListener("click", closeImageLightbox);
        }
        if (el.imageLightboxModal) {
            el.imageLightboxModal.addEventListener("click", (e) => {
                if (e.target === el.imageLightboxModal) closeImageLightbox();
            });
        }

        // Global Escape Key to close modals
        window.addEventListener("keydown", (e) => {
            if (e.key === "Escape") {
                closeImageLightbox();
                closeVisionModal();
                closeOsConfirmModal();
                if (el.examplesModal) el.examplesModal.style.display = "none";
                if (el.uploadModal) el.uploadModal.style.display = "none";
            }
        });
    }

    // Bootstrap Application
    window.addEventListener("DOMContentLoaded", async () => {
        initThreeJS();
        setupEventListeners();
        initVoiceRecognition();
        loadExamplesLibrary();

        // Start telemetry poll
        setInterval(pollTelemetry, 3000);
        pollTelemetry();
        loadStudentProgress();

        // Load initial Transformer model via catalog or Gemini
        await requestModelGeneration("Step-Down Electrical Transformer", false);
    });

})();
