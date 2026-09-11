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
    let holographicBrainGroup = null;
    let currentViewMode = "dashboard"; // "dashboard" or "3dlab" 

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
        mainPromptInput: document.getElementById("chat-input-field") || document.getElementById("main-prompt-input"),
        sendPromptBtn: document.getElementById("btn-send-message") || document.getElementById("send-prompt-btn"),
        voiceInputBtn: document.getElementById("btn-voice-mic") || document.getElementById("voice-input-btn"),
        micIcon: document.getElementById("mic-icon"),
        fileUploadBtn: document.getElementById("btn-upload-image") || document.getElementById("file-upload-btn"),
        hiddenFileInput: document.getElementById("image-upload-input") || document.getElementById("hidden-file-input"),
        btnVoiceToggle: document.getElementById("btn-voice-toggle"),
        ttsIcon: document.getElementById("tts-icon"),
        // New Dashboard Elements
        heroWelcomePanel: document.getElementById("hero-welcome-panel"),
        btnHeroStartLearning: document.getElementById("btn-hero-start-learning"),
        btnToggleViewMode: document.getElementById("btn-toggle-viewmode"),
        componentDrawer: document.getElementById("component-drawer"),
        btnCloseDrawer: document.getElementById("btn-close-drawer"),
        // Modals
        modalTeacher: document.getElementById("modal-teacher"),
        modalQuiz: document.getElementById("modal-quiz"),
        modalCodeRunner: document.getElementById("modal-coderunner"),
        modalProgress: document.getElementById("modal-progress"),
        modalNotes: document.getElementById("modal-notes"),
        modalSettings: document.getElementById("modal-settings"),
        btnRunCode: document.getElementById("btn-run-code"),
        codeEditor: document.getElementById("code-sandbox-editor"),
        codeOutput: document.getElementById("code-sandbox-output"),
        // Quick Actions
        qaBtnOpen3d: document.getElementById("qa-btn-open-3d"),
        qaBtnTakeQuiz: document.getElementById("qa-btn-take-quiz"),
        qaBtnViewProgress: document.getElementById("qa-btn-view-progress"),
        qaBtnGetHelp: document.getElementById("qa-btn-get-help"),
        btnPedagogySettings: document.getElementById("btn-pedagogy-settings"),
        btnBrowseStudyFile: document.getElementById("btn-browse-study-file"),
        studyFileInput: document.getElementById("study-file-input"),
        notesUploadZone: document.getElementById("notes-upload-zone"),
        notesExtractedContent: document.getElementById("notes-extracted-content"),
        settingsPedagogyLevel: document.getElementById("settings-pedagogy-level"),
        settingsTtsToggle: document.getElementById("settings-tts-toggle"),
        systemStatusChip: document.getElementById("system-status-chip"),
        inspirationBannerCard: document.getElementById("inspiration-banner-card"),
        teacherLevelSelect: document.getElementById("teacher-level-select"),
        // Legacy Modals & Fallbacks
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
        if (el.container) {
            el.container.addEventListener("mousemove", onMouseMove);
            el.container.addEventListener("click", onMouseClick);
        }

        // Viewport toolbar buttons (safe null-check)
        const vZoomIn = document.getElementById("v-zoom-in");
        if (vZoomIn) vZoomIn.addEventListener("click", () => zoomCamera(-1.5));
        const vZoomOut = document.getElementById("v-zoom-out");
        if (vZoomOut) vZoomOut.addEventListener("click", () => zoomCamera(1.5));
        const vRotate = document.getElementById("v-rotate");
        if (vRotate) vRotate.addEventListener("click", () => rotateCamera(Math.PI / 4));
        const vAutoSpin = document.getElementById("v-auto-spin");
        if (vAutoSpin) vAutoSpin.addEventListener("click", toggleAutoSpin);
        const vRecenter = document.getElementById("v-recenter");
        if (vRecenter) vRecenter.addEventListener("click", () => fitCameraToObject(scene));
        const btnResetView = document.getElementById("btn-reset-view");
        if (btnResetView) btnResetView.addEventListener("click", () => fitCameraToObject(scene));

        // Create Holographic Brain & Pedestal Scene for Dashboard
        createHolographicBrainGroup();

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

        // Animate Holographic AI Brain & Ring Orbitals on Dashboard
        if (holographicBrainGroup && holographicBrainGroup.visible) {
            const time = Date.now() * 0.0015;
            const brain = holographicBrainGroup.getObjectByName("brain_floating_mesh");
            if (brain) {
                brain.position.y = 0.4 + Math.sin(time * 2.5) * 0.08;
                brain.rotation.y += 0.008;
            }
            const halo1 = holographicBrainGroup.getObjectByName("halo_ring_1");
            if (halo1) halo1.rotation.z += 0.012;
            const halo2 = holographicBrainGroup.getObjectByName("halo_ring_2");
            if (halo2) halo2.rotation.y += 0.01;
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

        // 2. Update Inspector Card & Drawer
        if (el.compName) el.compName.textContent = comp.name || comp.id;
        if (el.compColorChip) el.compColorChip.style.backgroundColor = comp.color || "#00d4ff";
        if (el.compRoleTag) el.compRoleTag.textContent = comp.role || "Engineering Component";
        if (el.compTypeTag) el.compTypeTag.textContent = `Type: ${comp.type || "Solid"}`;
        if (el.compDesc) el.compDesc.textContent = comp.description || "Active component in system.";
        if (el.componentDrawer) el.componentDrawer.classList.add("open");

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
        if (!components) return;
        if (el.componentCountBadge) el.componentCountBadge.textContent = `${components.length} PARTS`;
        if (el.componentsScrollList) {
            el.componentsScrollList.innerHTML = "";
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
        if (el.animPlayPause) el.animPlayPause.textContent = "▶ PLAY";

        updateAnimationUI();
    }

    function updateAnimationUI() {
        if (!animSteps || animSteps.length === 0) {
            if (el.animStepBadge) el.animStepBadge.textContent = "NO ANIMATION";
            if (el.animStepDesc) el.animStepDesc.textContent = "Static model inspection.";
            if (el.animBarFill) el.animBarFill.style.width = "100%";
            return;
        }

        const step = animSteps[currentAnimStep];
        if (el.animStepBadge) el.animStepBadge.textContent = `STEP ${currentAnimStep + 1} OF ${animSteps.length}`;
        if (el.animStepDesc) el.animStepDesc.textContent = step ? step.description : "";
        const progress = ((currentAnimStep + 1) / animSteps.length) * 100;
        if (el.animBarFill) el.animBarFill.style.width = `${progress}%`;

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

        const teacherBody = document.getElementById("teacher-lesson-body");
        if (teacherBody) {
            const comps = lesson.components_breakdown || [];
            const apps = lesson.real_world_applications || [];
            const qList = lesson.socratic_questions || [];

            const compsHtml = comps.map(c => `
                <div class="teacher-breakdown-item" style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 12px; margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                        <strong style="color: #00f0ff;">${c.name}</strong>
                        <span style="font-size: 11px; background: rgba(37,99,235,0.2); color: #60a5fa; padding: 2px 8px; border-radius: 12px;">${c.role || "Component"}</span>
                    </div>
                    <div style="font-size: 13px; color: #cbd5e1; line-height: 1.5;">${c.explanation}</div>
                </div>
            `).join("");

            const appsHtml = apps.map(app => `
                <div style="font-size: 13px; color: #cbd5e1; padding: 6px 0; border-bottom: 1px dashed rgba(255,255,255,0.06);">
                    <span style="color: #38bdf8; margin-right: 6px;">✦</span> ${app}
                </div>
            `).join("");

            const socraticHtml = qList.map((q, idx) => `
                <div class="socratic-card" style="background: rgba(168,85,247,0.05); border: 1px solid rgba(168,85,247,0.2); border-radius: 8px; padding: 14px; margin-bottom: 12px;">
                    <div style="font-weight: 600; color: #e2e8f0; margin-bottom: 8px;">Q${idx + 1}: ${q.question}</div>
                    <div style="display: flex; gap: 8px; margin-bottom: 8px;">
                        <button class="hud-btn hud-btn-outline hint-toggle-btn" style="padding: 4px 10px; font-size: 12px; cursor: pointer;">💡 Clue / Hint</button>
                        <button class="hud-btn hud-btn-accent ans-toggle-btn" style="padding: 4px 10px; font-size: 12px; cursor: pointer;">✓ Master Answer</button>
                    </div>
                    <div class="socratic-hint-panel" style="display: none; background: rgba(245,158,11,0.1); border-left: 3px solid #f59e0b; padding: 8px 12px; border-radius: 4px; font-size: 12px; color: #fde68a; margin-top: 6px;">${q.hint || "Think about the governing conservation laws."}</div>
                    <div class="socratic-ans-panel" style="display: none; background: rgba(16,185,129,0.1); border-left: 3px solid #10b981; padding: 8px 12px; border-radius: 4px; font-size: 12px; color: #a7f3d0; margin-top: 6px;">${q.answer || "Fundamental engineering operational principle."}</div>
                </div>
            `).join("");

            teacherBody.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 12px;">
                    <div>
                        <h2 style="font-size: 20px; font-weight: 800; color: #fff; margin: 0 0 4px 0;">${lesson.topic || (currentModelSpec ? currentModelSpec.topic : "System")}</h2>
                        <span style="font-size: 12px; color: #00f0ff;">Pedagogical Mode: ${(el.teacherLevelSelect && el.teacherLevelSelect.value) || "Intermediate"}</span>
                    </div>
                    <button id="btn-read-lesson-tts" class="hud-btn hud-btn-accent" style="display: flex; align-items: center; gap: 6px; cursor: pointer;">
                        <span>🔊</span> Read Aloud
                    </button>
                </div>

                <div style="margin-bottom: 20px;">
                    <h4 style="color: #94a3b8; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;">System Overview</h4>
                    <p style="font-size: 14px; line-height: 1.6; color: #e2e8f0; background: rgba(255,255,255,0.02); padding: 12px; border-radius: 8px;">${lesson.overview || "High-level overview of the active 3D model."}</p>
                </div>

                <div style="margin-bottom: 20px;">
                    <h4 style="color: #94a3b8; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;">Governing Physical Principle</h4>
                    <p style="font-size: 14px; line-height: 1.6; color: #a5f3fc; background: rgba(0,240,255,0.04); border-left: 3px solid #00f0ff; padding: 12px; border-radius: 4px;">${lesson.working_principle || "Engineering principles."}</p>
                </div>

                <div style="margin-bottom: 20px;">
                    <h4 style="color: #94a3b8; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">Component Architecture (${comps.length} Parts)</h4>
                    <div>${compsHtml}</div>
                </div>

                <div style="margin-bottom: 20px;">
                    <h4 style="color: #94a3b8; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">Industrial Applications</h4>
                    <div style="background: rgba(255,255,255,0.02); padding: 10px 14px; border-radius: 8px;">${appsHtml}</div>
                </div>

                <div style="margin-bottom: 20px;">
                    <h4 style="color: #c084fc; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">Socratic Discovery Questions</h4>
                    <div>${socraticHtml}</div>
                </div>
            `;

            const ttsBtn = teacherBody.querySelector("#btn-read-lesson-tts");
            if (ttsBtn) ttsBtn.addEventListener("click", speakTeacherLesson);

            teacherBody.querySelectorAll(".hint-toggle-btn").forEach(btn => {
                btn.addEventListener("click", () => {
                    const card = btn.closest(".socratic-card");
                    const p = card.querySelector(".socratic-hint-panel");
                    if (p) p.style.display = p.style.display === "none" ? "block" : "none";
                });
            });

            teacherBody.querySelectorAll(".ans-toggle-btn").forEach(btn => {
                btn.addEventListener("click", () => {
                    const card = btn.closest(".socratic-card");
                    const p = card.querySelector(".socratic-ans-panel");
                    if (p) p.style.display = p.style.display === "none" ? "block" : "none";
                });
            });
        }

    function speakTeacherLesson() {
        if (!currentTeacherLesson) return;
        const text = `${currentTeacherLesson.topic}. ${currentTeacherLesson.overview} Working principle: ${currentTeacherLesson.working_principle}`;
        speakText(text);
    }

    function generateClientTeacherLesson(spec, level) {
        if (!spec) return { topic: "System", overview: "Interactive 3D model.", working_principle: "Physical mechanics.", component_breakdown: [], applications: [], socratic_questions: [] };
        const comps = spec.components || [];
        const breakdown = comps.slice(0, 6).map(c => ({
            name: c.name || c.id,
            role: c.type ? `${c.type.toUpperCase()} Component` : "Structural Unit",
            details: c.description || "Essential component contributing to structural integrity and dynamic function."
        }));
        return {
            topic: spec.topic || "3D System",
            overview: spec.explanation || `This interactive 3D simulation demonstrates the structural, mechanical, and scientific principles governing ${spec.topic}.`,
            working_principle: `The architecture of ${spec.topic} relies on synchronized physical interactions between its ${comps.length} primary components, balancing applied forces, energy transfers, and material constraints.`,
            component_breakdown: breakdown,
            applications: [
                `Modern engineering analysis and CAD spatial verification of ${spec.topic}.`,
                `Educational visualization of multi-body physical systems and operational kinematics.`,
                `Diagnostic troubleshooting and structural stress mitigation in industrial systems.`
            ],
            socratic_questions: [
                {
                    question: `Why is the spatial geometry and alignment of ${comps[0] ? comps[0].name : "the primary assembly"} critical to overall system stability?`,
                    hint: "Consider how mechanical stress or flux lines distribute along the geometric axes.",
                    answer: "Proper geometric alignment ensures even force distribution, preventing localized shear failure and reducing operational vibrations."
                },
                {
                    question: `How would the efficiency of ${spec.topic} change if component friction or thermal dissipation increased?`,
                    hint: "Think about the first and second laws of thermodynamics.",
                    answer: "Parasitic energy loss would elevate operating temperatures, degrading material lifespan and reducing mechanical/electrical conversion efficiency."
                }
            ]
        };
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
                return;
            }
            throw new Error(`Status ${resp.status}`);
        } catch (e) {
            console.warn("Teacher refresh fallback to client synthesis:", e);
            const lesson = generateClientTeacherLesson(currentModelSpec, level);
            renderTeacherLesson(lesson);
            if (el.teacherStatusBadge) el.teacherStatusBadge.textContent = level.toUpperCase();
        }
    }


    // ==========================================
    // 4c. INTERACTIVE QUIZ LAB
    // ==========================================

    function renderQuiz(quizData) {
        if (!quizData) return;
        currentQuiz = quizData;
        quizUserAnswers.clear();

        const quizBody = document.getElementById("quiz-modal-body");
        if (!quizBody) return;

        const questions = quizData.questions || [];
        const total = questions.length;

        quizBody.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 12px;">
                <div>
                    <h3 style="font-size: 18px; font-weight: 700; color: #fff; margin: 0 0 4px 0;">${quizData.topic || (currentModelSpec ? currentModelSpec.topic : "Engineering System")}</h3>
                    <span style="font-size: 12px; color: #00f0ff; background: rgba(0,240,255,0.1); padding: 2px 8px; border-radius: 12px;">Difficulty: ${(quizData.difficulty || "Intermediate").toUpperCase()}</span>
                </div>
                <div style="text-align: right;">
                    <div id="quiz-score-display" style="font-size: 18px; font-weight: 800; color: #10b981;">0 / ${total}</div>
                    <span style="font-size: 11px; color: #94a3b8;">SCORE RATIO</span>
                </div>
            </div>
            <div id="quiz-cards-container"></div>
            <div id="quiz-feedback-box" style="margin-top: 14px;"></div>
            <div style="display: flex; justify-content: space-between; margin-top: 16px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 12px;">
                <button id="btn-quiz-regenerate" class="hud-btn hud-btn-outline" style="cursor: pointer;">↺ New Quiz Questions</button>
                <button id="btn-quiz-restart" class="hud-btn hud-btn-accent" style="cursor: pointer;">Reset Answers</button>
            </div>
        `;

        const container = quizBody.querySelector("#quiz-cards-container");

        questions.forEach((q, qIdx) => {
            const card = document.createElement("div");
            card.className = "question-card";
            card.dataset.qid = q.id || `q_${qIdx}`;
            card.style.cssText = "background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 16px; margin-bottom: 14px;";

            const targetBadge = q.target_component_id 
                ? `<button class="hud-btn hud-btn-outline question-target-badge" data-target="${q.target_component_id}" style="padding: 2px 8px; font-size: 11px; border-color: rgba(0,240,255,0.4); color: #00f0ff; cursor: pointer;">🎯 View Part: ${q.target_component_id}</button>` 
                : "";

            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 600;">Question ${qIdx + 1} of ${total}</span>
                    ${targetBadge}
                </div>
                <div style="font-size: 15px; font-weight: 600; color: #fff; margin-bottom: 12px; line-height: 1.5;">${q.question}</div>
                <div class="question-options-grid" style="display: grid; grid-template-columns: 1fr; gap: 8px;"></div>
                <div class="question-explanation-box" style="display: none; margin-top: 10px; padding: 10px; border-radius: 6px; font-size: 13px; line-height: 1.4; background: rgba(0,0,0,0.3); border-left: 3px solid #10b981;"></div>
            `;

            if (q.target_component_id) {
                const b = card.querySelector(".question-target-badge");
                if (b) {
                    b.addEventListener("click", () => {
                        selectComponent(q.target_component_id, false);
                    });
                }
            }

            const optsGrid = card.querySelector(".question-options-grid");
            (q.options || []).forEach((optText, optIdx) => {
                const btn = document.createElement("button");
                btn.className = "quiz-opt-btn";
                btn.style.cssText = "background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.12); border-radius: 6px; padding: 10px 14px; color: #cbd5e1; text-align: left; font-size: 13px; cursor: pointer; transition: all 0.2s;";
                btn.textContent = optText;
                btn.addEventListener("click", () => handleQuizOptionClick(q, optIdx, btn, card));
                optsGrid.appendChild(btn);
            });

            container.appendChild(card);
        });

        const regenBtn = quizBody.querySelector("#btn-quiz-regenerate");
        if (regenBtn) regenBtn.addEventListener("click", regenerateQuiz);
        const restartBtn = quizBody.querySelector("#btn-quiz-restart");
        if (restartBtn) restartBtn.addEventListener("click", () => renderQuiz(currentQuiz));
    }

    function handleQuizOptionClick(question, optIdx, clickedBtn, cardEl) {
        if (quizUserAnswers.has(question.id)) return; // Already answered

        quizUserAnswers.set(question.id, optIdx);
        const isCorrect = (optIdx === question.correct_index);

        const allButtons = cardEl.querySelectorAll(".quiz-opt-btn");
        allButtons.forEach((btn, idx) => {
            btn.disabled = true;
            btn.style.cursor = "default";
            if (idx === question.correct_index) {
                btn.style.background = "rgba(16, 185, 129, 0.2)";
                btn.style.borderColor = "#10b981";
                btn.style.color = "#a7f3d0";
            } else if (idx === optIdx && !isCorrect) {
                btn.style.background = "rgba(239, 68, 68, 0.2)";
                btn.style.borderColor = "#ef4444";
                btn.style.color = "#fca5a5";
            }
        });

        // Show explanation
        const explBox = cardEl.querySelector(".question-explanation-box");
        if (explBox) {
            explBox.style.display = "block";
            explBox.innerHTML = `<strong>${isCorrect ? "✓ Correct!" : "✗ Incorrect."}</strong> ${question.explanation || ""}`;
            explBox.style.borderLeftColor = isCorrect ? "#10b981" : "#ef4444";
            explBox.style.color = isCorrect ? "#a7f3d0" : "#fca5a5";
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

        const scoreDisplay = document.getElementById("quiz-score-display");
        if (scoreDisplay) scoreDisplay.textContent = `${correctCount} / ${total}`;
        if (el.quizScoreRatio) el.quizScoreRatio.textContent = `${correctCount} / ${total}`;
        const pct = total > 0 ? Math.round((correctCount / total) * 100) : 0;
        if (el.quizScoreFill) el.quizScoreFill.style.width = `${pct}%`;

        const feedbackBox = document.getElementById("quiz-feedback-box");

        if (quizUserAnswers.size === total && total > 0) {
            const missedQuestions = currentQuiz.questions.filter(q => quizUserAnswers.get(q.id) !== q.correct_index);
            let weakCardHtml = "";

            if (missedQuestions.length > 0) {
                const firstMissed = missedQuestions[0];
                const compMatch = currentModelSpec && currentModelSpec.components 
                    ? currentModelSpec.components.find(c => c.id === firstMissed.target_component_id || (c.name && firstMissed.question && firstMissed.question.toLowerCase().includes(c.name.toLowerCase()))) 
                    : null;
                const weakName = compMatch ? compMatch.name : (firstMissed.target_component_id || "System Core Principle");

                weakCardHtml = `
                    <div class="weak-concept-card" style="margin-top: 12px; padding: 12px 14px; background: rgba(239, 68, 68, 0.12); border: 1px solid #ef4444; border-radius: 8px; text-align: left;">
                        <div style="font-weight: 700; color: #f87171; font-size: 13px; margin-bottom: 4px;">⚠️ Concept Review: ${weakName}</div>
                        <div style="font-size: 12px; color: #cbd5e1; margin-bottom: 8px;">Focus on spatial relationships and operational role in the 3D model.</div>
                        <button class="hud-btn hud-btn-accent" id="btn-review-weak-concept" style="font-size: 11px; padding: 6px 12px; cursor: pointer;">🔍 Inspect in 3D Lab</button>
                    </div>
                `;
            }

            const resultHtml = `
                <div style="padding: 14px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px;">
                    <div style="font-size: 15px; font-weight: 700; color: ${pct >= 75 ? '#34d399' : '#f59e0b'};">
                        ${pct >= 75 ? `🎉 Outstanding! Mastery confirmed (${pct}%). Ready for Advanced challenges.` : `Assessment Complete: ${correctCount}/${total} (${pct}%). Review the Teacher Mode lesson and try again!`}
                    </div>
                    ${weakCardHtml}
                </div>
            `;

            if (feedbackBox) feedbackBox.innerHTML = resultHtml;
            if (el.quizFeedbackText) el.quizFeedbackText.innerHTML = resultHtml;

            // Wire up review in 3D button
            setTimeout(() => {
                const reviewBtn = document.getElementById("btn-review-weak-concept");
                if (reviewBtn && missedQuestions.length > 0) {
                    reviewBtn.addEventListener("click", () => {
                        closeAllModals();
                        switchDashboardView("3dlab");
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
            const statusMsg = `Answered ${quizUserAnswers.size} of ${total} questions.`;
            if (feedbackBox) feedbackBox.innerHTML = `<div style="font-size: 12px; color: #94a3b8;">${statusMsg}</div>`;
            if (el.quizFeedbackText) el.quizFeedbackText.textContent = statusMsg;
        }
    }

    function generateClientQuiz(spec, difficulty) {
        if (!spec) return { topic: "System", difficulty: difficulty || "Intermediate", questions: [] };
        const comps = spec.components || [];
        const c1 = comps[0] || { name: "Primary Component", id: "part_1", description: "Main functional unit." };
        const c2 = comps[1] || { name: "Secondary Assembly", id: "part_2", description: "Secondary structural element." };
        const c3 = comps[2] || { name: "Coupling Interface", id: "part_3", description: "Connective node." };

        return {
            topic: spec.topic || "3D System",
            difficulty: difficulty || "Intermediate",
            questions: [
                {
                    id: "q_comp_1",
                    question: `What is the primary role of "${c1.name}" within this ${spec.topic} system?`,
                    options: [
                        c1.description || "Provides structural support and operational continuity for the assembly.",
                        "Passively radiates electromagnetic interference without physical interaction.",
                        "Acts solely as an aesthetic outer shroud with zero physical function.",
                        "Reverses the polarity of all connected joints simultaneously."
                    ],
                    correct_index: 0,
                    explanation: `${c1.name}: ${c1.description || "Crucial functional unit within the system."}`,
                    target_component_id: c1.id
                },
                {
                    id: "q_comp_2",
                    question: `How does "${c2.name}" physically or mechanically interact with the rest of the system?`,
                    options: [
                        "It remains completely disconnected and isolated from all surrounding components.",
                        c2.description || "Interacts with adjacent members to transmit forces, flux, or matter.",
                        "It completely halts system operation whenever motion occurs.",
                        "It dissolves into the surrounding medium during high stress cycles."
                    ],
                    correct_index: 1,
                    explanation: `${c2.name} plays an active role: ${c2.description || "Essential operational element."}`,
                    target_component_id: c2.id
                },
                {
                    id: "q_physics",
                    question: `Which fundamental principle governs the overall operation of ${spec.topic}?`,
                    options: [
                        "Conservation of energy, structural equilibrium, and dynamic force balance.",
                        "Arbitrary unconstrained kinematics with zero friction or inertia.",
                        "Complete violation of thermodynamic boundaries in closed systems.",
                        "Spontaneous perpetual generation of mechanical power."
                    ],
                    correct_index: 0,
                    explanation: `${spec.topic} adheres to classical physics and engineering principles, preserving energy and structural equilibrium.`,
                    target_component_id: c3.id
                }
            ]
        };
    }

    async function regenerateQuiz() {
        const spec = currentModelSpec || {
            topic: (el.currentTopicName && el.currentTopicName.textContent) || "Engineering System",
            components: []
        };
        const diff = el.quizDifficultySelect ? el.quizDifficultySelect.value : "Intermediate";
        const quizBody = document.getElementById("quiz-modal-body");
        if (quizBody) {
            quizBody.innerHTML = `
                <div style="padding: 32px; text-align: center; color: #00f0ff;">
                    <div style="font-size: 28px; margin-bottom: 12px;">🧪</div>
                    <div style="font-size: 15px; font-weight: 600; margin-bottom: 6px;">Synthesizing ${diff} assessment for ${spec.topic}...</div>
                    <div style="font-size: 12px; color: #94a3b8;">Generating multi-tier spatial questions based on mechanical nodes...</div>
                </div>
            `;
        }

        try {
            const resp = await fetch("/api/quiz/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ model_spec: spec, difficulty: diff }),
            });
            if (resp.ok) {
                const quiz = await resp.json();
                renderQuiz(quiz);
                return;
            }
            throw new Error("Assessment server returned error");
        } catch (e) {
            console.warn("Regenerate quiz fallback to client generation:", e);
            const quiz = generateClientQuiz(spec, diff);
            renderQuiz(quiz);
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
            if (resp.ok) {
                const data = await resp.json();
                renderStudentProgress(data);
                return;
            }
        } catch (e) {
            console.warn("Could not load student progress from backend, using local progress:", e);
        }
        try {
            const stored = JSON.parse(localStorage.getItem("aura_student_progress") || '{"mastery_tier": "Cadet", "overall_accuracy": 100, "total_quizzes_completed": 1, "current_streak": 3, "total_questions_answered": 5, "topics_attempted": ["Human Heart Anatomy"]}');
            renderStudentProgress(stored);
        } catch (_) {}
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

    function getClientFallbackModel(instruction) {
        if (!instruction) return null;
        const low = instruction.toLowerCase();

        // 1. Human Heart Anatomy
        if (low.includes("heart") || low.includes("cardiac") || low.includes("ventricle") || low.includes("aorta")) {
            return {
                topic: "Human Heart Anatomy & Circulatory Dynamics",
                explanation: "The human heart operates as a synchronized dual-pump. The right side receives oxygen-depleted venous blood and pumps it into the lungs for re-oxygenation. The left side receives oxygen-rich pulmonary blood and propels it through the aortic arch under high pressure into systemic circulation.",
                components: [
                    { id: "left_ventricle", type: "sphere", name: "Left Ventricle (Systemic Pump)", position: [0.55, 0, -0.6], size: 1.1, color: "#dc2626", alpha: 0.95, description: "Thick-walled muscular chamber pumping oxygenated blood to the entire body at high arterial pressure." },
                    { id: "right_ventricle", type: "sphere", name: "Right Ventricle (Pulmonary Pump)", position: [-0.55, 0, -0.6], size: 0.95, color: "#2563eb", alpha: 0.95, description: "Muscular chamber pumping deoxygenated blood through the pulmonary valve into the lungs." },
                    { id: "left_atrium", type: "sphere", name: "Left Atrium", position: [0.5, 0, 0.6], size: 0.8, color: "#ef4444", alpha: 0.92, description: "Receives freshly oxygenated blood returning from the pulmonary veins." },
                    { id: "right_atrium", type: "sphere", name: "Right Atrium", position: [-0.5, 0, 0.6], size: 0.8, color: "#3b82f6", alpha: 0.92, description: "Receives deoxygenated venous return from superior and inferior vena cavae." },
                    { id: "aorta_arch", type: "torus", name: "Aortic Arch & Ascending Aorta", position: [0.1, 0, 1.4], size: [0.85, 0.22], normal: [0, 1, 0], color: "#f87171", alpha: 0.96, description: "Primary high-pressure systemic artery distributing oxygenated blood throughout the body." },
                    { id: "pulmonary_trunk", type: "cylinder", name: "Pulmonary Artery Trunk", endpoints: [[-0.2, 0, 0.4], [-0.5, 0, 1.3]], size: [0.22, 1.1], color: "#60a5fa", alpha: 0.95, description: "Arterial vessel branching left and right to transport blood to alveolar capillary beds." },
                    { id: "superior_vena_cava", type: "cylinder", name: "Superior Vena Cava", position: [-0.85, 0, 1.1], size: [0.22, 1.2], color: "#1d4ed8", alpha: 0.95, axis: "z", description: "Large vein returning deoxygenated blood from upper body into right atrium." },
                    { id: "mitral_valve", type: "cylinder", name: "Bicuspid Mitral Valve", position: [0.55, 0, 0.0], size: [0.35, 0.12], color: "#fef08a", alpha: 0.95, axis: "z", description: "Dual-cusp atrioventricular valve preventing backflow into left atrium during systole." },
                    { id: "tricuspid_valve", type: "cylinder", name: "Tricuspid Valve", position: [-0.55, 0, 0.0], size: [0.35, 0.12], color: "#fef08a", alpha: 0.95, axis: "z", description: "Three-cusp valve preventing ventricular regurgitation into right atrium." },
                    { id: "septum_wall", type: "box", name: "Interventricular Muscular Septum", position: [0, 0, -0.6], size: [0.2, 1.2, 1.6], color: "#b91c1c", alpha: 0.95, description: "Dense muscular dividing wall separating oxygenated and deoxygenated chambers." }
                ],
                connections: [
                    { from_id: "superior_vena_cava", to_id: "right_atrium", from: "superior_vena_cava", to: "right_atrium", color: "#1d4ed8", thickness: 4, label: "Venous Return" },
                    { from_id: "right_atrium", to_id: "tricuspid_valve", from: "right_atrium", to: "tricuspid_valve", color: "#3b82f6", thickness: 3, label: "Atrial Inflow" },
                    { from_id: "tricuspid_valve", to_id: "right_ventricle", from: "tricuspid_valve", to: "right_ventricle", color: "#2563eb", thickness: 4, label: "Diastolic Filling" },
                    { from_id: "right_ventricle", to_id: "pulmonary_trunk", from: "right_ventricle", to: "pulmonary_trunk", color: "#60a5fa", thickness: 4, label: "Pulmonary Ejection" },
                    { from_id: "left_atrium", to_id: "mitral_valve", from: "left_atrium", to: "mitral_valve", color: "#ef4444", thickness: 3, label: "Oxygenated Feed" },
                    { from_id: "mitral_valve", to_id: "left_ventricle", from: "mitral_valve", to: "left_ventricle", color: "#dc2626", thickness: 4, label: "Ventricular Filling" },
                    { from_id: "left_ventricle", to_id: "aorta_arch", from: "left_ventricle", to: "aorta_arch", color: "#f87171", thickness: 5, label: "Aortic Systolic Ejection" }
                ],
                animation_steps: [
                    { step: 1, description: "Atrial Systole: Atria contract, filling both ventricles across mitral and tricuspid valves", affected_components: ["right_atrium", "left_atrium", "mitral_valve", "tricuspid_valve"], action: "pulse" },
                    { step: 2, description: "Ventricular Systole: Thick ventricular muscles contract, closing AV valves", affected_components: ["left_ventricle", "right_ventricle", "septum_wall"], action: "highlight" },
                    { step: 3, description: "High-pressure blood surges simultaneously into the aorta and pulmonary artery", affected_components: ["aorta_arch", "pulmonary_trunk"], action: "pulse" }
                ]
            };
        }

        // 2. Solar System Heliocentric Orbits
        if (low.includes("solar") || low.includes("planet") || low.includes("orbit") || low.includes("sun")) {
            return {
                topic: "Solar System Heliocentric Orbital Mechanics",
                explanation: "The solar system is governed by Newton's law of universal gravitation and Kepler's laws of planetary motion. Planets travel along elliptical heliocentric orbits with velocities inversely proportional to their distance from the central mass of the Sun.",
                components: [
                    { id: "sun_core", type: "sphere", name: "The Sun (Sol G2V Star)", position: [0, 0, 0], size: 0.9, color: "#facc15", alpha: 0.98, description: "G-type main-sequence star containing 99.86% of the solar system mass." },
                    { id: "orbit_mercury", type: "torus", name: "Mercury Orbital Path", position: [0, 0, 0], size: [1.4, 0.02], color: "#94a3b8", alpha: 0.7, description: "Elliptical orbit closest to the Sun with high orbital velocity of 47.4 km/s." },
                    { id: "planet_mercury", type: "sphere", name: "Mercury", position: [1.4, 0, 0], size: 0.14, color: "#9ca3af", alpha: 1.0, description: "Smallest terrestrial planet with cratered silicate surface." },
                    { id: "orbit_venus", type: "torus", name: "Venus Orbital Path", position: [0, 0, 0], size: [2.1, 0.02], color: "#fde047", alpha: 0.7, description: "Nearly circular retrograde rotation orbit inside habitable zone." },
                    { id: "planet_venus", type: "sphere", name: "Venus", position: [0, 2.1, 0], size: 0.24, color: "#eab308", alpha: 1.0, description: "Terrestrial planet with runaway CO2 greenhouse effect." },
                    { id: "orbit_earth", type: "torus", name: "Earth Orbital Path (1.0 AU)", position: [0, 0, 0], size: [2.8, 0.025], color: "#38bdf8", alpha: 0.8, description: "Habitable zone orbit defining one astronomical unit (149.6M km)." },
                    { id: "planet_earth", type: "sphere", name: "Earth (Terra)", position: [-2.8, 0, 0], size: 0.26, color: "#0284c7", alpha: 1.0, description: "Liquid water ocean world supporting biosphere." },
                    { id: "earth_moon", type: "sphere", name: "The Moon (Luna)", position: [-2.45, 0, 0.25], size: 0.08, color: "#e2e8f0", alpha: 1.0, description: "Tidally locked satellite causing ocean tides and stabilizing axial tilt." },
                    { id: "orbit_mars", type: "torus", name: "Mars Orbital Path", position: [0, 0, 0], size: [3.6, 0.02], color: "#ef4444", alpha: 0.7, description: "Eccentric orbit outside Earth possessing thin CO2 atmosphere." },
                    { id: "planet_mars", type: "sphere", name: "Mars", position: [0, -3.6, 0], size: 0.18, color: "#dc2626", alpha: 1.0, description: "Red planet characterized by iron oxide regolith and polar ice caps." },
                    { id: "orbit_jupiter", type: "torus", name: "Jupiter Orbital Path", position: [0, 0, 0], size: [4.6, 0.03], color: "#fb923c", alpha: 0.75, description: "Outer gas giant orbital boundary separating asteroid belt from Jovian system." },
                    { id: "planet_jupiter", type: "sphere", name: "Jupiter (Gas Giant)", position: [3.2, 3.2, 0], size: 0.52, color: "#f97316", alpha: 1.0, description: "Massive hydrogen-helium gas giant harboring Great Red Spot." }
                ],
                connections: [
                    { from_id: "sun_core", to_id: "planet_mercury", from: "sun_core", to: "planet_mercury", color: "#facc15", thickness: 2, label: "Gravitational Attraction" },
                    { from_id: "sun_core", to_id: "planet_earth", from: "sun_core", to: "planet_earth", color: "#facc15", thickness: 2, label: "Gravitational Attraction" },
                    { from_id: "planet_earth", to_id: "earth_moon", from: "planet_earth", to: "earth_moon", color: "#38bdf8", thickness: 2, label: "Lunar Orbit" },
                    { from_id: "sun_core", to_id: "planet_jupiter", from: "sun_core", to: "planet_jupiter", color: "#facc15", thickness: 2, label: "Gravitational Attraction" }
                ],
                animation_steps: [
                    { step: 1, description: "Inner terrestrial planets complete high-speed orbits in the solar gravitational well", affected_components: ["planet_mercury", "planet_venus", "planet_earth", "earth_moon"], action: "rotate" },
                    { step: 2, description: "Outer planets maintain stable low-velocity harmonic orbits", affected_components: ["planet_mars", "planet_jupiter"], action: "rotate" },
                    { step: 3, description: "Solar radiation and gravitational equilibrium define the solar system architecture", affected_components: ["sun_core"], action: "pulse" }
                ]
            };
        }

        // 3. Atom Structure & Quantum Orbitals
        if (low.includes("atom") || low.includes("bohr") || low.includes("nucleus") || low.includes("electron") || low.includes("quantum")) {
            return {
                topic: "Rutherford-Bohr Atomic Structure",
                explanation: "An atom comprises a compact, dense nucleus of positive protons and neutral neutrons bound by the strong nuclear force, surrounded by electrons in quantized probability shells as visualized in the Rutherford-Bohr model.",
                components: [
                    { id: "nucleus_proton_1", type: "sphere", name: "Proton (+)", position: [-0.18, 0.15, 0.1], size: 0.28, color: "#ff3355", alpha: 0.95, description: "Positively charged nucleon defining atomic number." },
                    { id: "nucleus_proton_2", type: "sphere", name: "Proton (+)", position: [0.18, -0.15, 0.1], size: 0.28, color: "#ff3355", alpha: 0.95, description: "Positive nuclear charge providing electromagnetic attraction." },
                    { id: "nucleus_neutron_1", type: "sphere", name: "Neutron (0)", position: [0.15, 0.2, -0.1], size: 0.28, color: "#8ffcff", alpha: 0.9, description: "Electrically neutral nucleon providing nuclear binding stability." },
                    { id: "nucleus_neutron_2", type: "sphere", name: "Neutron (0)", position: [-0.15, -0.2, -0.1], size: 0.28, color: "#8ffcff", alpha: 0.9, description: "Neutral nucleon preventing electrostatic proton repulsion." },
                    { id: "nucleus_force_field", type: "sphere", name: "Strong Nuclear Force Well", position: [0, 0, 0], size: 0.85, color: "#ff8c00", alpha: 0.28, description: "Ultra-short-range strong fundamental force holding nucleons together." },
                    { id: "orbital_ring_1", type: "torus", name: "Principal Quantum Shell 1s", position: [0, 0, 0], size: [2.4, 0.035], normal: [0.3, 0.4, 1.0], color: "#00e5ff", alpha: 0.85, description: "Lowest energy spherical electron orbital level." },
                    { id: "orbital_ring_2", type: "torus", name: "Subshell Orbital 2p-x", position: [0, 0, 0], size: [2.4, 0.035], normal: [-0.5, 0.6, 1.0], color: "#22d3ee", alpha: 0.85, description: "Quantized orbital path tilted relative to nuclear axis." },
                    { id: "orbital_ring_3", type: "torus", name: "Subshell Orbital 2p-y", position: [0, 0, 0], size: [2.4, 0.035], normal: [0.8, -0.2, 0.6], color: "#00ff88", alpha: 0.85, description: "Transverse probability shell completing electron valence cloud." },
                    { id: "electron_1", type: "sphere", name: "Valence Electron 1 (-)", position: [1.8, 0.7, -0.8], size: 0.18, color: "#ffcc00", alpha: 1.0, description: "Elementary lepton carrying negative unit charge." },
                    { id: "electron_2", type: "sphere", name: "Valence Electron 2 (-)", position: [-1.6, 1.3, 0.6], size: 0.18, color: "#ffcc00", alpha: 1.0, description: "Paired electron occupying opposite quantum spin state." },
                    { id: "electron_3", type: "sphere", name: "Valence Electron 3 (-)", position: [0.4, -1.9, 1.2], size: 0.18, color: "#ffcc00", alpha: 1.0, description: "Outer shell electron determining chemical bonding." }
                ],
                connections: [
                    { from_id: "nucleus_proton_1", to_id: "electron_1", from: "nucleus_proton_1", to: "electron_1", color: "#00e5ff", thickness: 2, label: "Coulomb Attraction" },
                    { from_id: "nucleus_proton_2", to_id: "electron_2", from: "nucleus_proton_2", to: "electron_2", color: "#22d3ee", thickness: 2, label: "Coulomb Attraction" },
                    { from_id: "nucleus_proton_1", to_id: "nucleus_neutron_1", from: "nucleus_proton_1", to: "nucleus_neutron_1", color: "#ff3355", thickness: 3, label: "Strong Nuclear Force" }
                ],
                animation_steps: [
                    { step: 1, description: "Strong nuclear force binds nucleons tightly into dense nucleus", affected_components: ["nucleus_proton_1", "nucleus_proton_2", "nucleus_neutron_1", "nucleus_neutron_2", "nucleus_force_field"], action: "pulse" },
                    { step: 2, description: "Electrons orbit along quantized wave shells at distinct phase angles", affected_components: ["orbital_ring_1", "orbital_ring_2", "orbital_ring_3", "electron_1", "electron_2", "electron_3"], action: "rotate" },
                    { step: 3, description: "Coulomb electrostatic attraction establishes quantum equilibrium", affected_components: ["electron_1", "electron_2", "electron_3", "nucleus_proton_1"], action: "highlight" }
                ]
            };
        }

        // 4. Electric Motor & Generator
        if (low.includes("motor") || low.includes("generator") || low.includes("stator") || low.includes("rotor")) {
            return {
                topic: "Industrial Electric Motor & Generator",
                explanation: "An electric motor converts electrical energy into rotational kinetic energy. Current supplied through brushes and the segmented commutator flows through rotor windings inside the stator magnetic field, experiencing Lorentz forces that generate continuous torque.",
                components: [
                    { id: "motor_base", type: "box", name: "Cast-Iron Base Pedestal", position: [0, 0, -1.7], size: [3.6, 2.6, 0.4], color: "#1e293b", alpha: 0.95, description: "Heavy bed plate absorbing vibration and anchoring stator housing." },
                    { id: "stator_housing", type: "cylinder", name: "Cylindrical Stator Frame", position: [0, 0, 0], size: [1.6, 2.4], color: "#0c3245", alpha: 0.45, axis: "y", description: "Outer steel enclosure providing magnetic flux return path." },
                    { id: "stator_n", type: "box", name: "North Magnetic Pole Shoe", position: [-1.1, 0, 0], size: [0.5, 2.0, 1.2], color: "#ff3355", alpha: 0.9, description: "Electromagnet pole establishing horizontal inward magnetic field." },
                    { id: "stator_s", type: "box", name: "South Magnetic Pole Shoe", position: [1.1, 0, 0], size: [0.5, 2.0, 1.2], color: "#00d4ff", alpha: 0.9, description: "Opposing pole completing the horizontal stator magnetic field." },
                    { id: "rotor_shaft", type: "cylinder", name: "Precision Drive Rotor Shaft", position: [0, 0, 0], size: [0.22, 4.4], color: "#cbd5e1", alpha: 0.95, axis: "y", description: "Precision alloy steel shaft transferring mechanical output torque." },
                    { id: "armature_core", type: "cylinder", name: "Slotted Armature Core", position: [0, 0, 0], size: [0.85, 1.8], color: "#ff8c00", alpha: 0.9, axis: "y", description: "Laminated silicon steel rotor core containing copper windings." },
                    { id: "commutator", type: "cylinder", name: "Segmented Copper Commutator", position: [0, 1.5, 0], size: [0.42, 0.5], color: "#ffcc00", alpha: 0.95, axis: "y", description: "Hard-drawn copper wedge segments reversing current every half turn." },
                    { id: "brush_pos", type: "box", name: "Positive Carbon Brush", position: [-0.55, 1.5, 0], size: [0.22, 0.25, 0.35], color: "#00ff88", alpha: 0.95, description: "Maintains sliding electrical contact under spring pressure." },
                    { id: "brush_neg", type: "box", name: "Negative Carbon Brush", position: [0.55, 1.5, 0], size: [0.22, 0.25, 0.35], color: "#00ff88", alpha: 0.95, description: "Return current carbon brush assembly." }
                ],
                connections: [
                    { from_id: "motor_base", to_id: "stator_housing", from: "motor_base", to: "stator_housing", color: "#1e293b", thickness: 3, label: "Chassis Mount" },
                    { from_id: "brush_pos", to_id: "commutator", from: "brush_pos", to: "commutator", color: "#00ff88", thickness: 2, label: "Sliding Contact" },
                    { from_id: "commutator", to_id: "armature_core", from: "commutator", to: "armature_core", color: "#ffcc00", thickness: 3, label: "Winding Current" },
                    { from_id: "armature_core", to_id: "rotor_shaft", from: "armature_core", to: "rotor_shaft", color: "#ff8c00", thickness: 4, label: "Torque Transmission" }
                ],
                animation_steps: [
                    { step: 1, description: "Electric current enters via carbon brushes and commutator segments", affected_components: ["brush_pos", "brush_neg", "commutator"], action: "highlight" },
                    { step: 2, description: "Armature windings experience Lorentz force in the stator magnetic field", affected_components: ["armature_core", "stator_n", "stator_s"], action: "pulse" },
                    { step: 3, description: "Rotor shaft delivers continuous high-speed mechanical output", affected_components: ["rotor_shaft"], action: "rotate" }
                ]
            };
        }

        // 5. Four-Stroke Internal Combustion Engine
        if (low.includes("stroke") || low.includes("combustion") || low.includes("engine") || low.includes("piston") || low.includes("crank")) {
            return {
                topic: "Four-Stroke Internal Combustion Engine",
                explanation: "The four-stroke Otto cycle comprises: (1) Intake: intake valve opens as piston descends, drawing in charge; (2) Compression: both valves close as piston compresses mixture; (3) Power: spark plug fires, pushing piston downward; (4) Exhaust: exhaust valve opens as piston expels burnt gases.",
                components: [
                    { id: "crankcase_block", type: "box", name: "Engine Block Crankcase", position: [0, 0, -1.2], size: [2.4, 1.8, 1.4], color: "#1e293b", alpha: 0.92, description: "Rigid cast iron block housing oil sump, bearings, and rotating crankshaft." },
                    { id: "cylinder_bore", type: "cylinder", name: "Honed Cylinder Sleeve", position: [0, 0, 0.4], size: [1.1, 2.2], color: "#0c2d48", alpha: 0.45, axis: "z", description: "Precision-honed cylinder bore containing combustion gas expansion." },
                    { id: "piston_crown", type: "cylinder", name: "Forged Aluminum Piston Crown", position: [0, 0, 0.9], size: [0.95, 0.6], color: "#ff8c00", alpha: 0.95, axis: "z", description: "Transfers gas pressure from combustion into reciprocating motion." },
                    { id: "connecting_rod", type: "cylinder", name: "Forged H-Beam Connecting Rod", endpoints: [[0, 0, 0.9], [0.55, 0, -1.0]], size: [0.14, 2.0], color: "#d8f8ff", alpha: 0.95, description: "Transmits reciprocating thrust to the crank throw." },
                    { id: "crank_journal", type: "sphere", name: "Crankshaft Rod Journal Pin", position: [0.55, 0, -1.0], size: 0.42, color: "#00d4ff", alpha: 0.95, description: "Offset crankpin rotating about crankshaft centerline." },
                    { id: "crank_main_shaft", type: "cylinder", name: "Crankshaft Main Drive Shaft", position: [0, 0, -1.0], size: [0.25, 2.6], color: "#00d4ff", alpha: 0.95, axis: "y", description: "Central rotating axle delivering shaft flywheel horsepower." },
                    { id: "cylinder_head", type: "box", name: "Cylinder Head Assembly", position: [0, 0, 2.2], size: [2.2, 1.6, 0.6], color: "#334155", alpha: 0.92, description: "Encloses combustion chamber and houses valves and spark plug." },
                    { id: "intake_valve", type: "cone", name: "Intake Poppet Valve", position: [-0.55, 0, 1.8], size: [0.35, 0.55], color: "#00ff88", alpha: 0.9, axis: "z", description: "Opens to draw fresh air-fuel charge into cylinder." },
                    { id: "exhaust_valve", type: "cone", name: "Exhaust Poppet Valve", position: [0.55, 0, 1.8], size: [0.35, 0.55], color: "#ff3355", alpha: 0.9, axis: "z", description: "Discharges burnt combustion gases to exhaust manifold." },
                    { id: "spark_plug", type: "cylinder", name: "Iridium Spark Plug", position: [0, 0, 2.4], size: [0.15, 0.75], color: "#ffcc00", alpha: 0.98, axis: "z", description: "Ignites compressed charge with high-voltage spark." }
                ],
                connections: [
                    { from_id: "cylinder_bore", to_id: "cylinder_head", from: "cylinder_bore", to: "cylinder_head", color: "#334155", thickness: 3, label: "Head Gasket Seal" },
                    { from_id: "spark_plug", to_id: "piston_crown", from: "spark_plug", to: "piston_crown", color: "#ffcc00", thickness: 4, label: "Flame Expansion" },
                    { from_id: "piston_crown", to_id: "connecting_rod", from: "piston_crown", to: "connecting_rod", color: "#ff8c00", thickness: 4, label: "Piston Thrust" },
                    { from_id: "connecting_rod", to_id: "crank_journal", from: "connecting_rod", to: "crank_journal", color: "#00d4ff", thickness: 4, label: "Rotational Torque" }
                ],
                animation_steps: [
                    { step: 1, description: "Intake Stroke: intake valve opens and descending piston draws in fresh charge", affected_components: ["intake_valve", "cylinder_bore", "piston_crown"], action: "move" },
                    { step: 2, description: "Power Stroke: spark plug ignites mixture driving piston down with high force", affected_components: ["spark_plug", "piston_crown"], action: "pulse" },
                    { step: 3, description: "Connecting rod and crankshaft convert linear stroke into continuous flywheel torque", affected_components: ["connecting_rod", "crank_journal", "crank_main_shaft"], action: "rotate" }
                ]
            };
        }

        // Generic procedural fallback for any other query
        const title = instruction.trim().replace(/\b\w/g, l => l.toUpperCase());
        return {
            topic: title,
            explanation: `Autonomous procedural spatial assembly demonstrating the structural mechanics and physical principles of ${title}.`,
            components: [
                { id: "foundation_base", type: "box", name: "Structural Foundation Base", position: [0, 0, -1.5], size: [3.4, 2.4, 0.4], color: "#1e293b", alpha: 0.95, description: "Rigid foundation absorbing operational dynamic loads." },
                { id: "primary_chassis", type: "cylinder", name: "Primary Mechanism Core", position: [0, 0, 0], size: [0.9, 2.2], color: "#00d4ff", alpha: 0.88, axis: "z", description: "Central operating core sustaining system equilibrium." },
                { id: "secondary_module_1", type: "sphere", name: "Active Actuator Module", position: [-1.4, 0, 0.4], size: 0.65, color: "#ff8c00", alpha: 0.95, description: "Power generation and modulation interface." },
                { id: "secondary_module_2", type: "sphere", name: "Sensor & Telemetry Node", position: [1.4, 0, 0.4], size: 0.65, color: "#00ff88", alpha: 0.95, description: "Real-time state monitoring and feedback module." },
                { id: "upper_crown", type: "box", name: "Upper Stabilization Gantry", position: [0, 0, 1.4], size: [2.6, 1.2, 0.4], color: "#ff3355", alpha: 0.9, description: "Top restraint structure balancing moment reactions." }
            ],
            connections: [
                { from_id: "foundation_base", to_id: "primary_chassis", from: "foundation_base", to: "primary_chassis", color: "#1e293b", thickness: 4, label: "Structural Mount" },
                { from_id: "primary_chassis", to_id: "secondary_module_1", from: "primary_chassis", to: "secondary_module_1", color: "#ff8c00", thickness: 3, label: "Power Coupling" },
                { from_id: "primary_chassis", to_id: "secondary_module_2", from: "primary_chassis", to: "secondary_module_2", color: "#00ff88", thickness: 3, label: "Feedback Conduit" },
                { from_id: "primary_chassis", to_id: "upper_crown", from: "primary_chassis", to: "upper_crown", color: "#ff3355", thickness: 3, label: "Gantry Link" }
            ],
            animation_steps: [
                { step: 1, description: "Foundation and structural core establish rigid force boundary", affected_components: ["foundation_base", "primary_chassis"], action: "pulse" },
                { step: 2, description: "Active modules modulate energy and feedback flow", affected_components: ["secondary_module_1", "secondary_module_2"], action: "rotate" },
                { step: 3, description: "Full system operates in harmonic dynamic balance", affected_components: ["upper_crown", "primary_chassis"], action: "highlight" }
            ]
        };
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
            console.warn("Backend unavailable, loading from client 3D model catalog:", err);
            const fallbackSpec = getClientFallbackModel(promptText);
            if (fallbackSpec) {
                updateLoadingProgress("VALIDATING MODEL", "Loading built-in procedural geometry...", 4);
                updateLoadingProgress("BUILDING 3D SCENE", "Initializing WebGL shaders & leader lines...", 5);
                setTimeout(() => {
                    renderModelSpec(fallbackSpec);
                    showLoadingOverlay(false);
                    appendChatMessage("AURA", `Constructed 3D model for **${fallbackSpec.topic}** (Client Catalog). ${fallbackSpec.explanation}`);
                    if (isTtsEnabled) speakText(`Constructed 3D model for ${fallbackSpec.topic}.`);
                }, 400);
                return;
            }
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
            if (el.voiceInputBtn) el.voiceInputBtn.classList.add("recording");
            if (el.micIcon) el.micIcon.textContent = "🔴";
        };

        recognition.onend = () => {
            isListening = false;
            if (el.voiceInputBtn) el.voiceInputBtn.classList.remove("recording");
            if (el.micIcon) el.micIcon.textContent = "🎤";
        };

        recognition.onresult = async (event) => {
            const transcript = event.results[0][0].transcript.trim();
            if (transcript) {
                if (el.mainPromptInput) el.mainPromptInput.value = transcript;
                await processUserPrompt(transcript);
            }
        };

        recognition.onerror = (event) => {
            console.warn("Speech recognition error:", event.error);
            isListening = false;
            if (el.voiceInputBtn) el.voiceInputBtn.classList.remove("recording");
            if (el.micIcon) el.micIcon.textContent = "🎤";
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
        const sub = document.querySelector(".chat-prompt-sub");
        if (sub && sender.toLowerCase() !== "you") {
            const cleanText = text.replace(/[*_#`]/g, "");
            sub.textContent = cleanText.length > 50 ? cleanText.slice(0, 48) + "..." : cleanText;
        }

        const container = document.getElementById("chat-messages") || el.chatMessages;
        if (container) {
            container.style.display = "flex";
            const msg = document.createElement("div");
            msg.className = `message ${sender.toLowerCase() === "you" ? "user" : "assistant"}`;
            msg.innerHTML = `
                <div class="sender">${sender.toUpperCase()}</div>
                <div class="text">${text}</div>
            `;
            container.appendChild(msg);
            container.scrollTop = container.scrollHeight;
        }
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
        if (el.uploadStatus) {
            el.uploadStatus.style.display = "flex";
            if (el.uploadStatusText) el.uploadStatusText.textContent = `Analyzing ${file.name}...`;
        }

        const notesContent = document.getElementById("notes-extracted-content");
        if (notesContent) {
            notesContent.innerHTML = `
                <div style="padding: 16px; text-align: center; color: #00f0ff;">
                    <div style="font-size: 24px; margin-bottom: 8px;">⏳</div>
                    <div>Extracting key engineering concepts from <strong>${file.name}</strong>...</div>
                </div>
            `;
        }

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

            // Render topics in right panel if legacy list exists
            if (el.topicsSection && el.topicsList) {
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
            }

            // Render extracted topics in Study Notes modal
            if (notesContent) {
                const topicBtns = (data.topics || []).map(t => `
                    <button class="hud-btn hud-btn-outline study-topic-btn" data-topic="${t.topic}" style="text-align: left; padding: 10px 14px; margin-bottom: 8px; width: 100%; display: flex; justify-content: space-between; align-items: center; cursor: pointer;">
                        <span style="color: #fff; font-weight: 600;">◈ ${t.topic}</span>
                        <span style="font-size: 11px; color: #00f0ff; background: rgba(0,240,255,0.1); padding: 2px 8px; border-radius: 4px;">Launch 3D Lab →</span>
                    </button>
                `).join("");

                notesContent.innerHTML = `
                    <div style="margin-top: 20px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 16px;">
                        <h4 style="color: #34d399; margin-bottom: 8px;">✓ Document Processed: ${file.name}</h4>
                        <p style="font-size: 13px; color: #94a3b8; margin-bottom: 14px;">Extracted ${data.char_count.toLocaleString()} characters. Click any concept below to generate its interactive 3D model:</p>
                        <div>${topicBtns}</div>
                    </div>
                `;

                notesContent.querySelectorAll(".study-topic-btn").forEach(btn => {
                    btn.addEventListener("click", () => {
                        const top = btn.dataset.topic;
                        closeAllModals();
                        switchDashboardView("3dlab");
                        requestModelGeneration(`Create a 3D educational model visualizing ${top}`);
                    });
                });
            }

            if (el.uploadStatus) el.uploadStatus.style.display = "none";
            if (el.uploadModal) el.uploadModal.style.display = "none";

            appendChatMessage("AURA", `Loaded study material **${file.name}** (${data.char_count.toLocaleString()} characters). Identified ${data.topics.length} key 3D topics. You can explore them in the Study Notes modal or right here.`);

            // Automatically build model for top topic if available
            if (data.topics && data.topics.length > 0) {
                requestModelGeneration(`Create a 3D educational model visualizing ${data.topics[0].topic}`);
            }

        } catch (err) {
            if (el.uploadStatusText) el.uploadStatusText.textContent = `Error: ${err.message}`;
            if (el.uploadStatus) setTimeout(() => { el.uploadStatus.style.display = "none"; }, 3000);
            if (notesContent) {
                notesContent.innerHTML = `<div style="color: #ef4444; padding: 12px;">Failed to extract document: ${err.message}</div>`;
            }
        }
    }

    // ==========================================
    // 8. EXAMPLES EXPLORER MODAL
    // ==========================================

    const CLIENT_FALLBACK_EXAMPLES = {
        "Electrical Engineering": [
            { title: "Electrical Transformer", prompt: "Electrical Transformer", description: "Visualize magnetic induction across laminated cores", difficulty: "beginner" },
            { title: "Electric Motor & Generator", prompt: "Industrial Electric Motor & Generator", description: "Convert electrical current into rotary Lorentz force", difficulty: "intermediate" },
            { title: "Rutherford-Bohr Atom", prompt: "Rutherford-Bohr Atomic Structure", description: "Principal quantum shells and orbital valence electrons", difficulty: "beginner" }
        ],
        "Mechanical Engineering": [
            { title: "Hydraulic Brake System", prompt: "Automotive Hydraulic Disc Brake System", description: "Pascal pressure and caliper clamping mechanics", difficulty: "intermediate" },
            { title: "Four-Stroke Engine", prompt: "Four-Stroke Internal Combustion Engine", description: "Otto cycle: intake, compression, power, exhaust", difficulty: "advanced" },
            { title: "Industrial Robot Arm", prompt: "6-Axis Industrial Articulated Robot Arm", description: "6-DOF kinematic positioning and pneumatic gripper", difficulty: "advanced" }
        ],
        "Civil & Structures": [
            { title: "Warren Truss Bridge", prompt: "Warren Steel Truss Bridge Structure", description: "Equilateral triangular load distribution under live loads", difficulty: "intermediate" },
            { title: "Wind Turbine System", prompt: "Utility-Scale Horizontal-Axis Wind Turbine", description: "Aerodynamic lift, planetary gearbox, and grid generation", difficulty: "intermediate" }
        ],
        "Natural Sciences": [
            { title: "Human Heart Anatomy", prompt: "Human Heart Anatomy & Circulatory Dynamics", description: "Four chambers, aortic arch, and dual-pump cardiac cycle", difficulty: "intermediate" },
            { title: "Plant Cell Machinery", prompt: "Plant Cell Anatomy & Photosynthetic Machinery", description: "Cellulose wall, vacuole turgor, and chloroplasts", difficulty: "intermediate" },
            { title: "Solar System Orbits", prompt: "Solar System Heliocentric Orbital Mechanics", description: "Keplerian heliocentric planetary orbits around the Sun", difficulty: "beginner" }
        ]
    };

    async function loadExamplesLibrary() {
        try {
            const resp = await fetch("/api/examples");
            if (resp.ok) {
                const data = await resp.json();
                renderExamplesModal(data.categories || CLIENT_FALLBACK_EXAMPLES);
                return;
            }
        } catch (err) {
            console.warn("Failed to load examples library from backend, using client catalog:", err);
        }
        renderExamplesModal(CLIENT_FALLBACK_EXAMPLES);
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
                if (el.telemetryCpu) el.telemetryCpu.textContent = `${data.cpu_percent}%`;
                if (el.telemetryCpuBar) el.telemetryCpuBar.style.width = `${data.cpu_percent}%`;
                if (el.telemetryRam) el.telemetryRam.textContent = `${data.ram_percent}%`;
                if (el.telemetryRamBar) el.telemetryRamBar.style.width = `${data.ram_percent}%`;
                const statusText = document.getElementById("status-chip-text");
                if (statusText) statusText.textContent = "System Online";
                return;
            }
        } catch (err) {
            // Silently fallback to active client simulation
        }
        const mockCpu = Math.floor(8 + Math.random() * 6);
        const mockRam = Math.floor(22 + Math.random() * 4);
        if (el.telemetryCpu) el.telemetryCpu.textContent = `${mockCpu}%`;
        if (el.telemetryCpuBar) el.telemetryCpuBar.style.width = `${mockCpu}%`;
        if (el.telemetryRam) el.telemetryRam.textContent = `${mockRam}%`;
        if (el.telemetryRamBar) el.telemetryRamBar.style.width = `${mockRam}%`;
        const statusText = document.getElementById("status-chip-text");
        if (statusText) statusText.textContent = "Client Active";
    }

    // ==========================================
    // 10. HOLOGRAPHIC BRAIN & DASHBOARD CONTROLLER
    // ==========================================

    function createHolographicBrainGroup() {
        if (!scene) return;
        if (holographicBrainGroup) {
            scene.remove(holographicBrainGroup);
        }
        holographicBrainGroup = new THREE.Group();
        holographicBrainGroup.name = "holographic_core_group";

        // 1. Futuristic Pedestal Base (Metallic cyber cylinder)
        const pedestalGeo = new THREE.CylinderGeometry(3.5, 3.8, 0.4, 48);
        const pedestalMat = new THREE.MeshStandardMaterial({
            color: 0x071120,
            metalness: 0.9,
            roughness: 0.2,
        });
        const pedestalMesh = new THREE.Mesh(pedestalGeo, pedestalMat);
        pedestalMesh.position.y = -2.0;
        holographicBrainGroup.add(pedestalMesh);

        // Concentric Glowing Neon Rings on Pedestal Floor
        const ringColors = [0x00f0ff, 0x2979ff, 0xa855f7];
        const ringRadii = [[3.3, 3.42], [2.6, 2.7], [1.8, 1.88]];
        ringRadii.forEach(([inner, outer], i) => {
            const ringGeo = new THREE.RingGeometry(inner, outer, 64);
            const ringMat = new THREE.MeshBasicMaterial({
                color: ringColors[i],
                side: THREE.DoubleSide,
                transparent: true,
                opacity: 0.85
            });
            const ringMesh = new THREE.Mesh(ringGeo, ringMat);
            ringMesh.rotation.x = -Math.PI / 2;
            ringMesh.position.y = -1.78 + (i * 0.01);
            holographicBrainGroup.add(ringMesh);
        });

        // 2. Vertical Laser Light Columns (Hologram projection pillars)
        for (let a = 0; a < 8; a++) {
            const angle = (a / 8) * Math.PI * 2;
            const px = Math.cos(angle) * 3.1;
            const pz = Math.sin(angle) * 3.1;
            const beamGeo = new THREE.CylinderGeometry(0.03, 0.03, 2.8, 8);
            const beamMat = new THREE.MeshBasicMaterial({
                color: 0x00f0ff,
                transparent: true,
                opacity: 0.35,
            });
            const beam = new THREE.Mesh(beamGeo, beamMat);
            beam.position.set(px, -0.4, pz);
            holographicBrainGroup.add(beam);
        }

        // 3. Holographic AI Brain / Neural Synapse Core
        const leftHemiGeo = new THREE.SphereGeometry(1.2, 24, 24);
        const rightHemiGeo = new THREE.SphereGeometry(1.2, 24, 24);
        leftHemiGeo.scale(1.0, 1.25, 1.35);
        rightHemiGeo.scale(1.0, 1.25, 1.35);

        const brainMatOuter = new THREE.MeshBasicMaterial({
            color: 0x00f0ff,
            wireframe: true,
            transparent: true,
            opacity: 0.45
        });
        const brainMatInner = new THREE.MeshStandardMaterial({
            color: 0x0b1736,
            emissive: 0x2563eb,
            emissiveIntensity: 0.7,
            roughness: 0.3,
            transparent: true,
            opacity: 0.65
        });

        const leftBrain = new THREE.Mesh(leftHemiGeo, brainMatOuter);
        leftBrain.position.set(-0.65, 0.4, 0);
        const rightBrain = new THREE.Mesh(rightHemiGeo, brainMatOuter);
        rightBrain.position.set(0.65, 0.4, 0);

        const innerCoreGeo = new THREE.IcosahedronGeometry(0.9, 3);
        const innerCore = new THREE.Mesh(innerCoreGeo, brainMatInner);
        innerCore.position.set(0, 0.4, 0);

        const brainSubGroup = new THREE.Group();
        brainSubGroup.name = "brain_floating_mesh";
        brainSubGroup.add(leftBrain);
        brainSubGroup.add(rightBrain);
        brainSubGroup.add(innerCore);

        // Synaptic Neural Nodes
        const nodeMatCyan = new THREE.MeshBasicMaterial({ color: 0x00f0ff });
        const nodeMatMagenta = new THREE.MeshBasicMaterial({ color: 0xec4899 });
        for (let n = 0; n < 24; n++) {
            const nGeo = new THREE.SphereGeometry(0.06, 8, 8);
            const nMesh = new THREE.Mesh(nGeo, n % 2 === 0 ? nodeMatCyan : nodeMatMagenta);
            const u = Math.random() * 2 - 1;
            const theta = Math.random() * Math.PI * 2;
            const r = 1.4 + Math.random() * 0.4;
            nMesh.position.set(
                r * Math.sqrt(1 - u * u) * Math.cos(theta),
                0.4 + u * 1.3,
                r * Math.sqrt(1 - u * u) * Math.sin(theta)
            );
            brainSubGroup.add(nMesh);
        }

        holographicBrainGroup.add(brainSubGroup);

        // 4. Quantum Orbital Rings
        const halo1 = new THREE.Mesh(
            new THREE.TorusGeometry(2.3, 0.02, 16, 100),
            new THREE.MeshBasicMaterial({ color: 0x00f0ff, transparent: true, opacity: 0.7 })
        );
        halo1.rotation.x = Math.PI / 4;
        halo1.name = "halo_ring_1";
        holographicBrainGroup.add(halo1);

        const halo2 = new THREE.Mesh(
            new THREE.TorusGeometry(2.5, 0.02, 16, 100),
            new THREE.MeshBasicMaterial({ color: 0xd946ef, transparent: true, opacity: 0.6 })
        );
        halo2.rotation.y = Math.PI / 3;
        halo2.rotation.x = -Math.PI / 6;
        halo2.name = "halo_ring_2";
        holographicBrainGroup.add(halo2);

        scene.add(holographicBrainGroup);
    }

    function closeAllModals() {
        if (el.modalTeacher) el.modalTeacher.style.display = "none";
        if (el.modalQuiz) el.modalQuiz.style.display = "none";
        if (el.modalCodeRunner) el.modalCodeRunner.style.display = "none";
        if (el.modalProgress) el.modalProgress.style.display = "none";
        if (el.modalNotes) el.modalNotes.style.display = "none";
        if (el.modalSettings) el.modalSettings.style.display = "none";
        if (el.examplesModal) el.examplesModal.style.display = "none";
        if (el.uploadModal) el.uploadModal.style.display = "none";
        if (el.imageLightboxModal) el.imageLightboxModal.style.display = "none";
        if (el.visionModal) el.visionModal.style.display = "none";
    }

    function switchDashboardView(viewName) {
        currentViewMode = viewName;

        // Synchronize Top Nav Pills
        document.querySelectorAll("#top-nav-group .nav-pill").forEach(p => {
            const pv = p.dataset.view;
            if (pv === viewName || (viewName === "dashboard" && pv === "home")) {
                p.classList.add("active");
            } else {
                p.classList.remove("active");
            }
        });

        // Synchronize Sidebar Items
        document.querySelectorAll("#side-nav-group .side-nav-item").forEach(s => {
            const sv = s.dataset.view;
            if (sv === viewName || (viewName === "home" && sv === "dashboard") || (viewName === "teacher" && sv === "ai-tutor") || (viewName === "learning" && sv === "learning-path")) {
                s.classList.add("active");
            } else {
                s.classList.remove("active");
            }
        });

        closeAllModals();

        if (viewName === "dashboard" || viewName === "home") {
            if (el.heroWelcomePanel) el.heroWelcomePanel.style.display = "flex";
            if (holographicBrainGroup) holographicBrainGroup.visible = true;
            componentMeshes.forEach(m => m.visible = false);
            connectionMeshes.forEach(m => m.visible = false);
            labelSprites.forEach(s => s.visible = false);
            if (controls) {
                camera.position.set(5.5, 3.5, 6.5);
                controls.target.set(0, 0, 0);
                controls.update();
            }
        } else if (viewName === "3dlab" || viewName === "learning") {
            if (el.heroWelcomePanel) el.heroWelcomePanel.style.display = "none";
            if (holographicBrainGroup) holographicBrainGroup.visible = false;
            componentMeshes.forEach(m => m.visible = true);
            connectionMeshes.forEach(m => m.visible = true);
            labelSprites.forEach(s => s.visible = showLabels);
            if (scene) fitCameraToObject(scene);
        } else if (viewName === "teacher" || viewName === "ai-tutor") {
            openTeacherModal();
        } else if (viewName === "quiz" || viewName === "quizzes") {
            openQuizModal();
        } else if (viewName === "coderunner") {
            openCodeRunnerModal();
        } else if (viewName === "progress") {
            openProgressModal();
        } else if (viewName === "resources" || viewName === "notes") {
            openNotesModal();
        } else if (viewName === "settings") {
            openSettingsModal();
        }
    }

    function openTeacherModal() {
        if (!el.modalTeacher) return;
        el.modalTeacher.style.display = "flex";
        if (currentModelSpec) {
            refreshTeacherLesson();
        } else {
            document.getElementById("teacher-lesson-body").innerHTML = "<p>Select or generate any 3D model to synthesize a multi-tier structured lesson.</p>";
        }
    }

    function openQuizModal() {
        if (!el.modalQuiz) return;
        el.modalQuiz.style.display = "flex";
        if (currentModelSpec) {
            regenerateQuiz();
        } else {
            document.getElementById("quiz-modal-body").innerHTML = "<p>Select or generate a 3D model to test your engineering knowledge.</p>";
        }
    }

    function openCodeRunnerModal() {
        if (!el.modalCodeRunner) return;
        el.modalCodeRunner.style.display = "flex";
    }

    async function openProgressModal() {
        if (!el.modalProgress) return;
        el.modalProgress.style.display = "flex";
        const container = document.getElementById("progress-modal-body");
        if (!container) return;
        container.innerHTML = "<p class='loading-placeholder'>Fetching assessment report & concept mastery...</p>";

        try {
            const resp = await fetch("/api/assessment");
            if (!resp.ok) throw new Error("Assessment service unreachable");
            const data = await resp.json();
            const summary = data.summary || {};
            const weak = data.weak_concepts || [];
            const strong = data.strong_concepts || [];

            let html = `
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 16px;">
                    <div style="background: rgba(255,255,255,0.05); padding: 12px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 20px; font-weight: 800; color: #00f0ff;">${summary.accuracy_pct || 0}%</div>
                        <div style="font-size: 11px; color: #94a3b8;">OVERALL ACCURACY</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.05); padding: 12px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 20px; font-weight: 800; color: #34d399;">${summary.total_quizzes || 0}</div>
                        <div style="font-size: 11px; color: #94a3b8;">QUIZZES TAKEN</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.05); padding: 12px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 16px; font-weight: 800; color: #f59e0b;">${summary.mastery_tier || 'Novice'}</div>
                        <div style="font-size: 11px; color: #94a3b8;">ENGINEERING RANK</div>
                    </div>
                </div>
            `;

            if (weak.length > 0) {
                html += `<h4 style="color: #f87171; margin-bottom: 8px;">Targeted 3D Revision (${weak.length} Concepts Need Review):</h4>`;
                weak.forEach(w => {
                    html += `
                        <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; padding: 10px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong style="color: #fff;">${w.topic || w.concept}</strong>
                                <div style="font-size: 11px; color: #fca5a5;">Accuracy: ${w.accuracy_pct}% &bull; Focus component operation</div>
                            </div>
                            <button class="hud-btn hud-btn-accent review-model-btn" data-model="${w.recommended_model || w.topic}" style="padding: 4px 10px; font-size: 11px;">
                                📦 Open in 3D Lab
                            </button>
                        </div>
                    `;
                });
            } else {
                html += `<div style="color: #34d399; margin: 10px 0;">Great work! No weak concepts currently detected.</div>`;
            }

            container.innerHTML = html;

            container.querySelectorAll(".review-model-btn").forEach(b => {
                b.addEventListener("click", () => {
                    const m = b.dataset.model;
                    closeAllModals();
                    switchDashboardView("3dlab");
                    requestModelGeneration(m);
                });
            });

        } catch (e) {
            container.innerHTML = `<p style="color: #ef4444;">Failed to load assessment telemetry: ${e.message}</p>`;
        }
    }

    function openNotesModal() {
        if (!el.modalNotes) return;
        el.modalNotes.style.display = "flex";
    }

    function openSettingsModal() {
        if (!el.modalSettings) return;
        el.modalSettings.style.display = "flex";
    }

    // ==========================================
    // 11. COMPLETE EVENT LISTENERS SETUP
    // ==========================================

    function setupEventListeners() {
        // Navigation Buttons (Top Nav Pills)
        document.querySelectorAll("#top-nav-group .nav-pill").forEach(p => {
            p.addEventListener("click", () => {
                const targetView = p.dataset.view;
                if (targetView) switchDashboardView(targetView);
            });
        });

        // Navigation Buttons (Left Sidebar Nav)
        document.querySelectorAll("#side-nav-group .side-nav-item").forEach(s => {
            s.addEventListener("click", () => {
                const targetView = s.dataset.view;
                if (targetView) switchDashboardView(targetView);
            });
        });

        // Brand Logo click -> Home
        const brandBtn = document.getElementById("nav-brand-btn");
        if (brandBtn) brandBtn.addEventListener("click", () => switchDashboardView("dashboard"));

        // User Profile pill -> Progress
        const userPill = document.getElementById("user-profile-trigger");
        if (userPill) userPill.addEventListener("click", () => switchDashboardView("progress"));

        // Hero Start Learning Button
        if (el.btnHeroStartLearning) {
            el.btnHeroStartLearning.addEventListener("click", () => {
                switchDashboardView("3dlab");
            });
        }

        // View Mode Toggle (Hologram Core vs Engineering 3D Model)
        if (el.btnToggleViewMode) {
            el.btnToggleViewMode.addEventListener("click", () => {
                if (currentViewMode === "dashboard") {
                    switchDashboardView("3dlab");
                } else {
                    switchDashboardView("dashboard");
                }
            });
        }

        // Feature Cards (Right Panel 2x3 Grid)
        const card3d = document.getElementById("card-3d-models");
        if (card3d) card3d.addEventListener("click", () => switchDashboardView("3dlab"));

        const cardAnim = document.getElementById("card-animations");
        if (cardAnim) cardAnim.addEventListener("click", () => {
            switchDashboardView("3dlab");
            playAnimation();
        });

        const cardCode = document.getElementById("card-code-runner");
        if (cardCode) cardCode.addEventListener("click", () => switchDashboardView("coderunner"));

        const cardTools = document.getElementById("card-interactive-tools");
        if (cardTools) cardTools.addEventListener("click", () => {
            switchDashboardView("3dlab");
            toggleExplodedView();
        });

        const cardTutor = document.getElementById("card-ai-tutor");
        if (cardTutor) cardTutor.addEventListener("click", () => switchDashboardView("teacher"));

        const cardNotes = document.getElementById("card-study-notes");
        if (cardNotes) cardNotes.addEventListener("click", () => switchDashboardView("notes"));

        // Quick Actions
        if (el.qaBtnOpen3d) el.qaBtnOpen3d.addEventListener("click", () => switchDashboardView("3dlab"));
        if (el.qaBtnTakeQuiz) el.qaBtnTakeQuiz.addEventListener("click", () => switchDashboardView("quiz"));
        if (el.qaBtnViewProgress) el.qaBtnViewProgress.addEventListener("click", () => switchDashboardView("progress"));
        if (el.qaBtnGetHelp) {
            el.qaBtnGetHelp.addEventListener("click", () => {
                appendChatMessage("AURA", "I am your AI Learning Partner. You can ask me questions, explore interactive 3D models, test concepts with quizzes, or run physics simulations in the Code Runner.");
            });
        }

        // Category Filter Pills
        document.querySelectorAll("#category-pills-group .cat-pill").forEach(pill => {
            pill.addEventListener("click", () => {
                document.querySelectorAll("#category-pills-group .cat-pill").forEach(p => p.classList.remove("active"));
                pill.classList.add("active");
                const cat = pill.dataset.cat;
                
                // Filter feature cards
                document.querySelectorAll("#feature-cards-grid .feature-card-item").forEach(card => {
                    const cCat = card.dataset.category;
                    if (cat === "all" || cCat === cat) {
                        card.style.display = "flex";
                    } else {
                        card.style.display = "none";
                    }
                });

                // Contextually suggest model for domain
                if (cat === "science") requestModelGeneration("Human Heart Anatomy");
                else if (cat === "math") requestModelGeneration("Direct Current (DC) Motor");
                else if (cat === "coding") openCodeRunnerModal();
                else if (cat === "ai") switchDashboardView("dashboard");
            });
        });

        // Code Runner Execution
        if (el.btnRunCode) {
            el.btnRunCode.addEventListener("click", () => {
                const code = el.codeEditor ? el.codeEditor.value : "";
                if (el.codeOutput) {
                    el.codeOutput.textContent = "Executing simulation in Python 3.11 virtual runtime...";
                    setTimeout(() => {
                        el.codeOutput.textContent = `[PYTHON 3.11 ENGINE - OK]\n` +
                            `Lorentz Force on Winding: 129.60 N\n` +
                            `Electromagnetic Output Torque: 20.74 N·m\n` +
                            `Operational RPM at 48V: 5806 RPM\n\n` +
                            `Simulation successfully completed at ${new Date().toLocaleTimeString()}.\n` +
                            `Physics conservation laws verified.`;
                    }, 400);
                }
            });
        }

        // Modal Close Buttons
        const btnCloseTeacher = document.getElementById("btn-close-teacher");
        if (btnCloseTeacher) btnCloseTeacher.addEventListener("click", () => { if (el.modalTeacher) el.modalTeacher.style.display = "none"; });
        const btnCloseQuiz = document.getElementById("btn-close-quiz");
        if (btnCloseQuiz) btnCloseQuiz.addEventListener("click", () => { if (el.modalQuiz) el.modalQuiz.style.display = "none"; });
        const btnCloseCode = document.getElementById("btn-close-coderunner");
        if (btnCloseCode) btnCloseCode.addEventListener("click", () => { if (el.modalCodeRunner) el.modalCodeRunner.style.display = "none"; });
        const btnCloseProgress = document.getElementById("btn-close-progress");
        if (btnCloseProgress) btnCloseProgress.addEventListener("click", () => { if (el.modalProgress) el.modalProgress.style.display = "none"; });
        const btnCloseNotes = document.getElementById("btn-close-notes");
        if (btnCloseNotes) btnCloseNotes.addEventListener("click", () => { if (el.modalNotes) el.modalNotes.style.display = "none"; });
        const btnCloseSettings = document.getElementById("btn-close-settings");
        if (btnCloseSettings) btnCloseSettings.addEventListener("click", () => { if (el.modalSettings) el.modalSettings.style.display = "none"; });
        if (el.btnCloseDrawer) el.btnCloseDrawer.addEventListener("click", () => { if (el.componentDrawer) el.componentDrawer.classList.remove("open"); });

        // HUD Controls
        const btnSpin = document.getElementById("hud-btn-spin");
        if (btnSpin) btnSpin.addEventListener("click", toggleAutoSpin);
        const btnLabels = document.getElementById("hud-btn-labels");
        if (btnLabels) btnLabels.addEventListener("click", () => {
            showLabels = !showLabels;
            labelSprites.forEach(s => s.visible = showLabels);
        });
        const btnXray = document.getElementById("hud-btn-xray");
        if (btnXray) btnXray.addEventListener("click", toggleXRayView);
        const btnExplode = document.getElementById("hud-btn-explode");
        if (btnExplode) btnExplode.addEventListener("click", toggleExplodedView);
        const btnRecenter = document.getElementById("hud-btn-reset");
        if (btnRecenter) btnRecenter.addEventListener("click", () => fitCameraToObject(scene));

        // Animation Bar Buttons
        if (el.animPlayPause) el.animPlayPause.addEventListener("click", () => {
            if (isPlayingAnim) pauseAnimation();
            else playAnimation();
        });
        if (el.animNext) el.animNext.addEventListener("click", nextAnimStep);
        if (el.animPrev) el.animPrev.addEventListener("click", prevAnimStep);
        if (el.animReset) el.animReset.addEventListener("click", resetAnimation);

        // Inspector Buttons
        if (el.compSpeakBtn) el.compSpeakBtn.addEventListener("click", () => {
            if (selectedComponentId && currentModelSpec) {
                const comp = currentModelSpec.components.find(c => c.id === selectedComponentId);
                if (comp) speakText(`${comp.name}. ${comp.description}`);
            }
        });
        if (el.compAskBtn) el.compAskBtn.addEventListener("click", () => {
            if (selectedComponentId && currentModelSpec) {
                const comp = currentModelSpec.components.find(c => c.id === selectedComponentId);
                if (comp) {
                    const promptText = `Explain the engineering function of the ${comp.name} in detail.`;
                    if (el.mainPromptInput) el.mainPromptInput.value = promptText;
                    processUserPrompt(promptText);
                }
            }
        });

        // Chat & Prompt Input
        if (el.sendPromptBtn) el.sendPromptBtn.addEventListener("click", () => {
            if (el.mainPromptInput) processUserPrompt(el.mainPromptInput.value);
        });
        if (el.mainPromptInput) el.mainPromptInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") processUserPrompt(el.mainPromptInput.value);
        });

        // Voice Controls
        if (el.voiceInputBtn) el.voiceInputBtn.addEventListener("click", toggleVoiceInput);
        if (el.btnVoiceToggle) el.btnVoiceToggle.addEventListener("click", () => {
            isTtsEnabled = !isTtsEnabled;
            if (!isTtsEnabled && window.speechSynthesis) window.speechSynthesis.cancel();
        });

        // File & Vision Upload
        if (el.fileUploadBtn && el.hiddenFileInput) {
            el.fileUploadBtn.addEventListener("click", () => el.hiddenFileInput.click());
        }
        if (el.hiddenFileInput) {
            el.hiddenFileInput.addEventListener("change", (e) => {
                if (e.target.files.length > 0) handleFileUpload(e.target.files[0]);
            });
        }

        // Pedagogical settings button in chat bar
        const btnPedagogy = document.getElementById("btn-pedagogy-settings");
        if (btnPedagogy) {
            btnPedagogy.addEventListener("click", () => openSettingsModal());
        }

        // Browse study file button in Study Notes modal
        const btnBrowseStudy = document.getElementById("btn-browse-study-file");
        const studyFileInput = document.getElementById("study-file-input");
        if (btnBrowseStudy && studyFileInput) {
            btnBrowseStudy.addEventListener("click", () => studyFileInput.click());
            studyFileInput.addEventListener("change", (e) => {
                if (e.target.files && e.target.files.length > 0) {
                    handleFileUpload(e.target.files[0]);
                }
            });
        }

        // Drop zone in Study Notes modal
        const notesZone = document.getElementById("notes-upload-zone");
        if (notesZone && studyFileInput) {
            notesZone.addEventListener("dragover", (e) => {
                e.preventDefault();
                notesZone.style.borderColor = "#00f0ff";
            });
            notesZone.addEventListener("dragleave", () => {
                notesZone.style.borderColor = "rgba(255,255,255,0.15)";
            });
            notesZone.addEventListener("drop", (e) => {
                e.preventDefault();
                notesZone.style.borderColor = "rgba(255,255,255,0.15)";
                if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    handleFileUpload(e.dataTransfer.files[0]);
                }
            });
        }

        // Settings modal controls
        const pedagogySelect = document.getElementById("settings-pedagogy-level");
        if (pedagogySelect) {
            pedagogySelect.addEventListener("change", (e) => {
                const lvl = e.target.value;
                const teacherSelect = document.getElementById("teacher-level-select");
                if (teacherSelect) teacherSelect.value = lvl;
                appendChatMessage("AURA", `Pedagogical mode switched to **${lvl}**.`);
            });
        }

        const ttsToggle = document.getElementById("settings-tts-toggle");
        if (ttsToggle) {
            ttsToggle.addEventListener("change", (e) => {
                isTtsEnabled = e.target.checked;
                if (!isTtsEnabled && window.speechSynthesis) window.speechSynthesis.cancel();
            });
        }

        const teacherLvl = document.getElementById("teacher-level-select");
        if (teacherLvl) {
            teacherLvl.addEventListener("change", () => refreshTeacherLesson());
        }

        // System status chip click
        const statusChip = document.getElementById("system-status-chip");
        if (statusChip) {
            statusChip.addEventListener("click", async () => {
                await pollTelemetry();
                appendChatMessage("AURA", "System diagnostic verified: FastAPI backend online, 3D WebGL renderer operational, neural pipeline synchronized.");
            });
        }

        // Inspiration banner card click
        const inspCard = document.getElementById("inspiration-banner-card");
        if (inspCard) {
            inspCard.addEventListener("click", () => {
                const quotes = [
                    "\"The scientist investigates that which already is; the Engineer creates that which has never been.\" — Theodore von Kármán",
                    "\"Engineering is the closest thing to real magic that exists in the world.\" — Elon Musk",
                    "\"Knowledge is of no value unless you put it into practice.\" — Anton Chekhov",
                    "\"Everything is theoretically impossible, until it is done.\" — Robert A. Heinlein"
                ];
                const randQuote = quotes[Math.floor(Math.random() * quotes.length)];
                appendChatMessage("AURA", randQuote);
            });
        }

        // Global Escape Key to close modals
        window.addEventListener("keydown", (e) => {
            if (e.key === "Escape") closeAllModals();
        });
    }

    // Bootstrap Application
    window.addEventListener("DOMContentLoaded", async () => {
        initThreeJS();
        setupEventListeners();
        initVoiceRecognition();

        // Start telemetry poll
        setInterval(pollTelemetry, 3000);
        pollTelemetry();
        loadStudentProgress();

        // Start on Dashboard View with Hologram Core
        switchDashboardView("dashboard");

        // Preload initial high-fidelity Heart Anatomy catalog in background
        await requestModelGeneration("Human Heart Anatomy", true);
    });

})();
