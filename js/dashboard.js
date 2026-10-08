const API_SENSOR_URL = "/api/sensor";
const EXERCISE_SECONDS = 20;

const EXERCISES = [
    {
        name: "Loose Fist",
        instruction: "Slowly close your hand into a loose fist.",
        audio: "audio/exercise_1_instruction.mp3"
    },
    {
        name: "Fingertip Touching",
        instruction: "Touch each fingertip to your thumb in order.",
        audio: "audio/exercise_2_instruction.mp3"
    },
    {
        name: "Wrist Rotation",
        instruction: "Rotate your wrist gently and steadily.",
        audio: "audio/exercise_3_instruction.mp3"
    },
    {
        name: "Finger Tapping",
        instruction: "Tap your fingers clearly against the sensor pads.",
        audio: "audio/exercise_4_instruction.mp3"
    },
    {
        name: "Hand Wave",
        instruction: "Wave your hand slowly from side to side.",
        audio: "audio/exercise_5_instruction.mp3"
    }
];

const state = {
    sessionStarted: false,
    sessionStartTime: null,
    currentExercise: 0,
    completedExercises: 0,
    exerciseStartedAt: null,
    lastSensorAt: 0,
    timerId: null,
    sessionFinished: false
};

function $(id) {
    return document.getElementById(id);
}

function setText(id, value) {
    const element = $(id);

    if (element) {
        element.textContent = value;
    }
}

function setWidth(id, value) {
    const element = $(id);

    if (element) {
        element.style.width = `${Math.max(0, Math.min(100, value))}%`;
    }
}

function formatNumber(value, digits = 1) {
    if (!Number.isFinite(value)) {
        return "--";
    }

    return value.toFixed(digits);
}

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remaining = seconds % 60;
    return `${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`;
}

function updateConnection(connected) {
    const status = connected ? "Connected" : "Waiting for Glove";
    const dataStatus = connected ? "LIVE" : "WAITING";

    setText("connectionStatus", status);
    setText("systemStatus", status);
    setText("gloveStatus", connected ? "Online" : "Waiting");
    setText("gloveStatusText", connected ? "● Live sensor stream" : "● No sensor stream");
    setText("sensorDataStatus", dataStatus);
    setText("liveSensorText", dataStatus);
    setText("deviceConnection", connected ? "Connected" : "Waiting");
    setText("deviceConnectionType", connected ? "USB Serial" : "Not connected");
    setText("deviceDataStatus", connected ? "Live" : "Waiting");
    setText("connectionMethod", connected ? "USB Serial" : "USB / Wi-Fi");

    [
        "connectionDot",
        "systemStatusDot",
        "liveSensorDot"
    ].forEach((id) => {
        const element = $(id);

        if (element) {
            element.style.background = connected ? "#1ccf8a" : "#ffb84d";
            element.style.boxShadow = connected ? "0 0 14px rgba(28, 207, 138, 0.75)" : "none";
        }
    });
}

function updateSensorView(data) {
    if (!data || !data.connected) {
        updateConnection(false);
        return;
    }

    updateConnection(true);
    state.lastSensorAt = Date.now();

    const pitch = data.orientation?.pitch ?? 0;
    const roll = data.orientation?.roll ?? 0;
    const accel = data.accel ?? { x: 0, y: 0, z: 0 };
    const gyro = data.gyro ?? { x: 0, y: 0, z: 0 };
    const touch = data.touch ?? [0, 0, 0, 0, 0];
    const touchCount = touch.filter((value) => value > 0).length;
    const accelMagnitude = Math.sqrt(
        (accel.x * accel.x) +
        (accel.y * accel.y) +
        (accel.z * accel.z)
    );
    const gyroMagnitude = Math.sqrt(
        (gyro.x * gyro.x) +
        (gyro.y * gyro.y) +
        (gyro.z * gyro.z)
    );

    setText("wristValue", formatNumber(pitch, 1));
    setText("rollValue", formatNumber(roll, 1));
    setText("heroWrist", `${formatNumber(pitch, 0)}°`);
    setText("heroFlexion", `${touchCount} / 5`);
    setText("wristRange", Math.abs(pitch) > 35 ? "High angle" : "Normal");
    setText("rollRange", Math.abs(roll) > 35 ? "High angle" : "Normal");
    setWidth("wristBar", (Math.abs(pitch) / 90) * 100);
    setWidth("rollBar", (Math.abs(roll) / 90) * 100);

    setText("accelValue", formatNumber(accelMagnitude, 2));
    setText("accelX", formatNumber(accel.x, 2));
    setText("accelY", formatNumber(accel.y, 2));
    setText("accelZ", formatNumber(accel.z, 2));

    setText("gyroValue", formatNumber(gyroMagnitude, 1));
    setText("gyroX", formatNumber(gyro.x, 1));
    setText("gyroY", formatNumber(gyro.y, 1));
    setText("gyroZ", formatNumber(gyro.z, 1));

    setText("touchCount", String(touchCount));
    setText("touchState", touch.join(""));

    touch.forEach((value, index) => {
        setText(`touch${index + 1}`, value > 0 ? "ON" : "OFF");
    });
}

async function fetchJson(url) {
    const response = await fetch(url, {
        cache: "no-store"
    });

    if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
    }

    return response.json();
}

async function refreshSensorData() {
    const liveToggle = $("liveSensorToggle");

    if (liveToggle && !liveToggle.checked) {
        return;
    }

    try {
        const data = await fetchJson(API_SENSOR_URL);
        updateSensorView(data);
    } catch (error) {
        updateConnection(false);
    }
}

function startTimer() {
    if (state.timerId) {
        clearInterval(state.timerId);
    }

    state.timerId = setInterval(() => {
        if (!state.sessionStarted || !state.sessionStartTime) {
            return;
        }

        const sessionSeconds = Math.floor((Date.now() - state.sessionStartTime) / 1000);
        const exerciseSeconds = Math.floor((Date.now() - state.exerciseStartedAt) / 1000);
        const remaining = Math.max(0, EXERCISE_SECONDS - exerciseSeconds);

        setText("sessionTime", formatTime(sessionSeconds));
        setText("currentExerciseTime", `${formatTime(exerciseSeconds)} / 00:20`);
        setText("nextChange", `${remaining}s`);
        setText("nextChangeText", "Next exercise");

        if (exerciseSeconds >= EXERCISE_SECONDS) {
            advanceExercise();
        }
    }, 1000);
}

function playAudio(path) {
    const audio = new Audio(path);
    audio.play().catch(() => {});
}

function updateExerciseView() {
    const current = EXERCISES[state.currentExercise];
    const progress = Math.round((state.completedExercises / EXERCISES.length) * 100);

    setText("exerciseCount", `${state.completedExercises} / ${EXERCISES.length}`);
    setText("completedExercises", `${state.completedExercises} / ${EXERCISES.length}`);
    setText("exerciseNumber", `Exercise ${state.currentExercise + 1} / ${EXERCISES.length}`);
    setText("exerciseProgressPercent", `${progress}%`);
    setWidth("exerciseProgressBar", progress);

    if (current) {
        setText("currentExerciseName", current.name);
        setText("currentExerciseInstruction", current.instruction);
    }
}

function startSession() {
    state.sessionStarted = true;
    state.sessionStartTime = Date.now();
    state.exerciseStartedAt = Date.now();
    state.currentExercise = 0;
    state.completedExercises = 0;
    state.sessionFinished = false;

    setText("sessionStatus", "Session active");
    setText("currentExerciseStatus", "Running");
    setText("nextChange", `${EXERCISE_SECONDS}s`);
    setText("nextChangeText", "Next exercise");
    updateExerciseView();
    startTimer();
    playAudio(EXERCISES[0].audio);
}

function finishSession() {
    state.completedExercises = EXERCISES.length;
    state.sessionFinished = true;
    state.sessionStarted = false;

    if (state.timerId) {
        clearInterval(state.timerId);
        state.timerId = null;
    }

    updateExerciseView();
    setText("currentExerciseStatus", "Complete");
    setText("sessionStatus", "Session complete");
    setText("nextChange", "Done");
    setText("nextChangeText", "Session complete");
    playAudio("audio/great_work.mp3");
}

function advanceExercise() {
    if (!state.sessionStarted || state.sessionFinished) {
        return;
    }

    state.completedExercises = Math.min(
        EXERCISES.length,
        state.completedExercises + 1
    );

    if (state.completedExercises >= EXERCISES.length) {
        finishSession();
        return;
    }

    state.currentExercise = state.completedExercises;
    state.exerciseStartedAt = Date.now();
    setText("currentExerciseStatus", "Running");
    setText("nextChange", `${EXERCISE_SECONDS}s`);
    setText("nextChangeText", "Next exercise");
    updateExerciseView();
    playAudio(EXERCISES[state.currentExercise].audio);
}

function handleStartButton() {
    if (state.sessionStarted) {
        return;
    }

    startSession();
}

function handleSkipButton() {
    if (!state.sessionStarted || state.sessionFinished) {
        return;
    }

    advanceExercise();
}

function initNavigation() {
    document.querySelectorAll(".nav-item").forEach((item) => {
        item.addEventListener("click", () => {
            document.querySelectorAll(".nav-item").forEach((nav) => {
                nav.classList.remove("active");
            });
            item.classList.add("active");
        });
    });

    $("viewSensorsBtn")?.addEventListener("click", () => {
        location.hash = "sensors";
    });

    $("mobileMenu")?.addEventListener("click", () => {
        document.querySelector(".sidebar")?.classList.toggle("open");
    });
}

function initButtons() {
    $("startExerciseBtn")?.addEventListener("click", handleStartButton);
    $("skipExerciseBtn")?.addEventListener("click", handleSkipButton);

    $("logoutBtn")?.addEventListener("click", () => {
        sessionStorage.removeItem("gloveLoggedIn");
        window.location.href = "index.html";
    });
}

function initDashboard() {
    if (!sessionStorage.getItem("gloveLoggedIn")) {
        sessionStorage.setItem("gloveLoggedIn", "true");
    }

    initNavigation();
    initButtons();
    updateConnection(false);
    updateExerciseView();
    setText("nextChange", "20s");
    setText("nextChangeText", "Per exercise");
    refreshSensorData();
    setInterval(refreshSensorData, 500);
}

document.addEventListener("DOMContentLoaded", initDashboard);
