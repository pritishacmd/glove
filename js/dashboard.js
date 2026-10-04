/* =========================================================
   GLOVECARE AI DASHBOARD
   REAL ESP8266 SENSOR + AI + EXERCISE SESSION
========================================================= */


/* =========================================================
   LOGIN
========================================================= */

const loginStatus = sessionStorage.getItem("gloveLoggedIn");

if (loginStatus !== "true") {
    window.location.href = "index.html";
}


/* =========================================================
   BASIC DASHBOARD
========================================================= */

const navItems = document.querySelectorAll(".nav-item");
const sidebar = document.querySelector(".sidebar");
const mobileMenu = document.getElementById("mobileMenu");

navItems.forEach(item => {

    item.addEventListener("click", function() {

        navItems.forEach(nav => {
            nav.classList.remove("active");
        });

        this.classList.add("active");

        if (window.innerWidth <= 900) {
            sidebar.classList.remove("open");
        }

    });

});


const logoutBtn = document.getElementById("logoutBtn");

if (logoutBtn) {

    logoutBtn.addEventListener("click", function() {

        sessionStorage.removeItem("gloveLoggedIn");

        window.location.href = "index.html";

    });

}


if (mobileMenu) {

    mobileMenu.addEventListener("click", function() {

        sidebar.classList.toggle("open");

    });

}


const viewSensorsBtn =
    document.getElementById("viewSensorsBtn");

if (viewSensorsBtn) {

    viewSensorsBtn.addEventListener("click", function() {

        document.getElementById("sensors").scrollIntoView({
            behavior: "smooth"
        });

    });

}


/* =========================================================
   AI API
========================================================= */

const AI_API_URL = "http://127.0.0.1:8000";

let aiAPIConnected = false;


/* =========================================================
   CONNECTION STATE
========================================================= */

let sensorConnected = false;
let connectionType = "None";

let serialPort = null;
let serialReader = null;
let serialBuffer = "";

let sessionRunning = false;
let sessionSeconds = 0;
let sessionTimer = null;

let currentExerciseIndex = -1;
let completedExercises = 0;
let exerciseSeconds = 0;
let exerciseTimer = null;

let latestSensorData = null;


/* =========================================================
   AI REQUEST QUEUE
   Keeps real sensor samples in correct order.
========================================================= */

let aiRequestQueue = Promise.resolve();


/* =========================================================
   SESSION HISTORY
========================================================= */

const SESSION_HISTORY_KEY =
    "gloveCareSessionHistory";

let currentSessionRecord = null;


/* =========================================================
   EXERCISES
========================================================= */

const exercises = [

    {
        name: "Loose Fist",
        label: "exercise_1_loose_fist",
        instruction:
            "Make a loose fist with your thumb on the outside",
        audio:
            "audio/exercise_1_instruction.mp3"
    },

    {
        name: "Idle",
        label: "idle",
        instruction:
            "Relax your hand and keep your wrist still",
        audio:
            "audio/exercise_2_instruction.mp3"
    },

    {
        name: "Wrist Clockwise Rotation",
        label: "exercise_3_wrist_clockwise",
        instruction:
            "Rotate your wrist clockwise",
        audio:
            "audio/exercise_3_instruction.mp3"
    },

    {
        name: "Hand Wave",
        label: "exercise_4_hand_wave",
        instruction:
            "Wave your hand",
        audio:
            "audio/exercise_4_instruction.mp3"
    },

    {
        name: "Finger Typing",
        label: "exercise_5_finger_typing",
        instruction:
            "Move your fingers like you are typing on a keyboard",
        audio:
            "audio/exercise_5_instruction.mp3"
    }

];


const feedbackAudioFiles = [

    "audio/great_work.mp3",
    "audio/very_good.mp3",
    "audio/keep_going.mp3"

];


const instructionAudio = new Audio();
const feedbackAudio = new Audio();


/* =========================================================
   AI DETECTION SETTINGS
========================================================= */

const MIN_CONFIDENCE = 60;

/*
   A prediction must have reasonable confidence
   before entering the history.
*/

const STABLE_HISTORY_SIZE = 12;

/*
   Number of recent accepted predictions considered
   for stability.
*/

const REQUIRED_MAJORITY = 0.70;

/*
   At least 70% of the accepted predictions must
   agree before the prediction is considered stable.
*/

const REQUIRED_MATCHES = 8;

/*
   Number of stable matching predictions required
   before completing an exercise.
*/

const STRONG_ROLL_RANGE = 25;

/*
   Roll movement required for wrist rotation.
*/

const STRONG_GYRO_MOVEMENT = 35;

/*
   Approximate gyro movement threshold in degrees/second.
*/


/* =========================================================
   WRIST MOVEMENT HISTORY
========================================================= */

let wristRollHistory = [];
let gyroMagnitudeHistory = [];


function updateWristMovementHistory(
    roll,
    gyro
) {

    wristRollHistory.push(
        Number(roll) || 0
    );

    gyroMagnitudeHistory.push(
        Number(gyro) || 0
    );


    if (wristRollHistory.length > 20) {

        wristRollHistory.shift();

    }


    if (gyroMagnitudeHistory.length > 20) {

        gyroMagnitudeHistory.shift();

    }

}


function getWristRollRange() {

    if (
        wristRollHistory.length < 8
    ) {

        return 0;

    }


    const maximum =
        Math.max(
            ...wristRollHistory
        );


    const minimum =
        Math.min(
            ...wristRollHistory
        );


    return maximum - minimum;

}


function getMaximumGyroMovement() {

    if (
        gyroMagnitudeHistory.length === 0
    ) {

        return 0;

    }


    return Math.max(
        ...gyroMagnitudeHistory
    );

}


function hasStrongWristMovement() {

    const rollRange =
        getWristRollRange();


    const gyroMovement =
        getMaximumGyroMovement();


    return (
        rollRange >= STRONG_ROLL_RANGE &&
        gyroMovement >= STRONG_GYRO_MOVEMENT
    );

}


/* =========================================================
   AUDIO CONTROL
========================================================= */

function stopAllAudio() {

    instructionAudio.pause();
    instructionAudio.currentTime = 0;

    feedbackAudio.pause();
    feedbackAudio.currentTime = 0;

}


/* =========================================================
   PLAY INSTRUCTION
========================================================= */

function playInstruction(index) {

    return new Promise(resolve => {

        if (!exercises[index]) {

            resolve();

            return;
        }


        instructionAudio.pause();

        instructionAudio.currentTime = 0;

        instructionAudio.src =
            exercises[index].audio;


        instructionAudio.onended = function() {

            resolve();

        };


        instructionAudio.onerror = function() {

            console.log(
                "Instruction audio could not play."
            );

            resolve();

        };


        instructionAudio.play().catch(error => {

            console.log(
                "Instruction audio could not play:",
                error
            );

            resolve();

        });

    });

}


/* =========================================================
   PLAY FEEDBACK
========================================================= */

function playFeedback() {

    return new Promise(resolve => {

        const randomIndex =
            Math.floor(
                Math.random() *
                feedbackAudioFiles.length
            );


        feedbackAudio.pause();

        feedbackAudio.currentTime = 0;

        feedbackAudio.src =
            feedbackAudioFiles[randomIndex];


        feedbackAudio.onended = function() {

            resolve();

        };


        feedbackAudio.onerror = function() {

            console.log(
                "Feedback audio could not play."
            );

            resolve();

        };


        feedbackAudio.play().catch(error => {

            console.log(
                "Feedback audio could not play:",
                error
            );

            resolve();

        });

    });

}


/* =========================================================
   SMALL DELAY
========================================================= */

function wait(milliseconds) {

    return new Promise(resolve => {

        setTimeout(
            resolve,
            milliseconds
        );

    });

}


/* =========================================================
   TEST FEEDBACK BUTTON
========================================================= */

const testFeedbackBtn =
    document.getElementById(
        "testFeedbackBtn"
    );


if (testFeedbackBtn) {

    testFeedbackBtn.addEventListener(
        "click",
        async function() {

            await playFeedback();

        }
    );

}


/* =========================================================
   CONNECTION STATUS
========================================================= */

function updateConnectionStatus(
    connected,
    method
) {

    sensorConnected = connected;

    connectionType = method;


    const connectionStatus =
        document.getElementById(
            "connectionStatus"
        );

    const connectionMethod =
        document.getElementById(
            "connectionMethod"
        );

    const sensorDataStatus =
        document.getElementById(
            "sensorDataStatus"
        );

    const systemStatus =
        document.getElementById(
            "systemStatus"
        );

    const gloveStatus =
        document.getElementById(
            "gloveStatus"
        );

    const gloveStatusText =
        document.getElementById(
            "gloveStatusText"
        );

    const deviceConnection =
        document.getElementById(
            "deviceConnection"
        );

    const deviceConnectionType =
        document.getElementById(
            "deviceConnectionType"
        );

    const deviceDataStatus =
        document.getElementById(
            "deviceDataStatus"
        );

    const liveSensorText =
        document.getElementById(
            "liveSensorText"
        );


    if (connected) {

        connectionStatus.textContent =
            "Glove Connected";

        connectionMethod.textContent =
            method;

        sensorDataStatus.textContent =
            "LIVE";

        sensorDataStatus.style.color =
            "#55b895";

        systemStatus.textContent =
            "System Online";

        gloveStatus.textContent =
            "Connected";

        gloveStatusText.textContent =
            "● Real sensor stream";

        deviceConnection.innerHTML =
            "<span></span> Connected";

        deviceConnectionType.textContent =
            method;

        deviceDataStatus.textContent =
            "LIVE";

        liveSensorText.textContent =
            "LIVE";

    } else {

        connectionStatus.textContent =
            "Waiting for Glove";

        connectionMethod.textContent =
            "USB Serial";

        sensorDataStatus.textContent =
            "WAITING";

        sensorDataStatus.style.color =
            "";

        systemStatus.textContent =
            "Waiting for Glove";

        gloveStatus.textContent =
            "Waiting";

        gloveStatusText.textContent =
            "● No sensor stream";

        deviceConnection.innerHTML =
            "<span></span> Waiting";

        deviceConnectionType.textContent =
            "Not connected";

        deviceDataStatus.textContent =
            "Waiting";

        liveSensorText.textContent =
            "WAITING";

    }

}


/* =========================================================
   NUMBER FORMAT
========================================================= */

function formatNumber(
    value,
    decimals = 2
) {

    if (
        value === undefined ||
        value === null ||
        Number.isNaN(Number(value))
    ) {

        return "--";

    }


    return Number(value).toFixed(decimals);

}


/* =========================================================
   SENSOR DASHBOARD
========================================================= */

function updateSensorDashboard(data) {

    latestSensorData = data;


    const touch =
        data.touch ||
        [0, 0, 0, 0, 0];


    const accel =
        data.accel ||
        {
            x: 0,
            y: 0,
            z: 0
        };


    const gyro =
        data.gyro ||
        {
            x: 0,
            y: 0,
            z: 0
        };


    const orientation =
        data.orientation ||
        {
            pitch: 0,
            roll: 0
        };


    const pitch =
        Number(orientation.pitch) || 0;


    const roll =
        Number(orientation.roll) || 0;


    const touchCount =
        touch.reduce(
            (total, value) =>
                total +
                (Number(value) ? 1 : 0),
            0
        );


    document.getElementById(
        "wristValue"
    ).textContent =
        formatNumber(
            pitch,
            1
        );


    document.getElementById(
        "rollValue"
    ).textContent =
        formatNumber(
            roll,
            1
        );


    document.getElementById(
        "heroWrist"
    ).textContent =
        formatNumber(
            pitch,
            1
        ) + "°";


    document.getElementById(
        "heroFlexion"
    ).textContent =
        touchCount +
        " / 5";


    const pitchWidth =
        Math.min(
            Math.abs(pitch) / 90 * 100,
            100
        );


    const rollWidth =
        Math.min(
            Math.abs(roll) / 90 * 100,
            100
        );


    document.getElementById(
        "wristBar"
    ).style.width =
        pitchWidth + "%";


    document.getElementById(
        "rollBar"
    ).style.width =
        rollWidth + "%";


    document.getElementById(
        "wristRange"
    ).textContent =
        formatNumber(
            pitch,
            1
        ) + "°";


    document.getElementById(
        "rollRange"
    ).textContent =
        formatNumber(
            roll,
            1
        ) + "°";


    const accelerationMagnitude =
        Math.sqrt(
            accel.x * accel.x +
            accel.y * accel.y +
            accel.z * accel.z
        );


    const gyroMagnitude =
        Math.sqrt(
            gyro.x * gyro.x +
            gyro.y * gyro.y +
            gyro.z * gyro.z
        );


    document.getElementById(
        "accelValue"
    ).textContent =
        formatNumber(
            accelerationMagnitude,
            2
        );


    document.getElementById(
        "gyroValue"
    ).textContent =
        formatNumber(
            gyroMagnitude,
            1
        );


    document.getElementById(
        "accelX"
    ).textContent =
        formatNumber(
            accel.x,
            3
        );


    document.getElementById(
        "accelY"
    ).textContent =
        formatNumber(
            accel.y,
            3
        );


    document.getElementById(
        "accelZ"
    ).textContent =
        formatNumber(
            accel.z,
            3
        );


    document.getElementById(
        "gyroX"
    ).textContent =
        formatNumber(
            gyro.x,
            2
        );


    document.getElementById(
        "gyroY"
    ).textContent =
        formatNumber(
            gyro.y,
            2
        );


    document.getElementById(
        "gyroZ"
    ).textContent =
        formatNumber(
            gyro.z,
            2
        );


    document.getElementById(
        "touchCount"
    ).textContent =
        touchCount;


    document.getElementById(
        "touchActive"
    ).textContent =
        touchCount;


    document.getElementById(
        "touch1"
    ).textContent =
        Number(touch[0])
            ? "ACTIVE"
            : "OFF";


    document.getElementById(
        "touch2"
    ).textContent =
        Number(touch[1])
            ? "ACTIVE"
            : "OFF";


    document.getElementById(
        "touch3"
    ).textContent =
        Number(touch[2])
            ? "ACTIVE"
            : "OFF";


    document.getElementById(
        "touch4"
    ).textContent =
        Number(touch[3])
            ? "ACTIVE"
            : "OFF";


    document.getElementById(
        "touch5"
    ).textContent =
        Number(touch[4])
            ? "ACTIVE"
            : "OFF";


    document.getElementById(
        "touchState"
    ).textContent =
        touchCount > 0
            ? "Contact detected"
            : "No contact";


    document.getElementById(
        "analysisSensor"
    ).textContent =
        "LIVE";


    document.getElementById(
        "deviceDataStatus"
    ).textContent =
        "LIVE";


    /* -----------------------------------------
       SAVE MOVEMENT DATA FOR AI LOGIC
    ----------------------------------------- */

    updateWristMovementHistory(
        roll,
        gyroMagnitude
    );

}


/* =========================================================
   SERIAL CONNECTION
========================================================= */

async function connectUSBSerial() {

    if (!("serial" in navigator)) {

        alert(
            "Web Serial is not available.\n\n" +
            "Please use Google Chrome or Microsoft Edge."
        );

        return;

    }


    try {

        serialPort =
            await navigator.serial.requestPort();


        await serialPort.open({
            baudRate: 115200
        });


        updateConnectionStatus(
            true,
            "USB Serial • 115200 baud"
        );


        serialBuffer = "";

        readSerialData();

    }

    catch (error) {

        console.log(
            "USB serial connection failed:",
            error
        );

    }

}


/* =========================================================
   SERIAL READER
========================================================= */

async function readSerialData() {

    if (!serialPort) {
        return;
    }


    const decoder =
        new TextDecoder();


    while (
        serialPort &&
        serialPort.readable
    ) {

        serialReader =
            serialPort.readable.getReader();


        try {

            while (true) {

                const {
                    value,
                    done
                } =
                    await serialReader.read();


                if (done) {
                    break;
                }


                if (!value) {
                    continue;
                }


                serialBuffer +=
                    decoder.decode(value);


                const lines =
                    serialBuffer.split("\n");


                serialBuffer =
                    lines.pop();


                for (const line of lines) {

                    parseSerialLine(
                        line.trim()
                    );

                }

            }

        }

        catch (error) {

            console.log(
                "Serial reading error:",
                error
            );

        }

        finally {

            serialReader.releaseLock();

            serialReader = null;

        }

    }

}


/* =========================================================
   PARSE REAL ESP8266 DATA
========================================================= */

function parseSerialLine(line) {

    if (!line.startsWith("DATA,")) {
        return;
    }


    const parts =
        line.split(",");


    if (parts.length !== 13) {
        return;
    }


    const timestamp =
        Number(parts[1]);


    const t1 =
        Number(parts[2]);

    const t2 =
        Number(parts[3]);

    const t3 =
        Number(parts[4]);

    const t4 =
        Number(parts[5]);

    const t5 =
        Number(parts[6]);


    const rawAx =
        Number(parts[7]);

    const rawAy =
        Number(parts[8]);

    const rawAz =
        Number(parts[9]);


    const rawGx =
        Number(parts[10]);

    const rawGy =
        Number(parts[11]);

    const rawGz =
        Number(parts[12]);


    if (
        [
            timestamp,
            t1,
            t2,
            t3,
            t4,
            t5,
            rawAx,
            rawAy,
            rawAz,
            rawGx,
            rawGy,
            rawGz
        ].some(
            value =>
                Number.isNaN(value)
        )
    ) {

        return;

    }


    /* -----------------------------------------
       MPU6050 RAW → PHYSICAL VALUES
    ----------------------------------------- */

    const ax =
        rawAx / 16384;


    const ay =
        rawAy / 16384;


    const az =
        rawAz / 16384;


    const gx =
        rawGx / 131;


    const gy =
        rawGy / 131;


    const gz =
        rawGz / 131;


    /* -----------------------------------------
       ORIENTATION
    ----------------------------------------- */

    const pitch =
        Math.atan2(
            ax,
            Math.sqrt(
                ay * ay +
                az * az
            )
        ) *
        180 /
        Math.PI;


    const roll =
        Math.atan2(
            ay,
            az
        ) *
        180 /
        Math.PI;


    const sensorData = {

        touch: [
            t1,
            t2,
            t3,
            t4,
            t5
        ],

        accel: {
            x: ax,
            y: ay,
            z: az
        },

        gyro: {
            x: gx,
            y: gy,
            z: gz
        },

        orientation: {
            pitch: pitch,
            roll: roll
        },

        timestamp: timestamp

    };


    /* -----------------------------------------
       UPDATE DASHBOARD WITH REAL DATA
    ----------------------------------------- */

    updateSensorDashboard(
        sensorData
    );


    updateConnectionStatus(
        true,
        "USB Serial • 115200 baud"
    );


    /* -----------------------------------------
       SEND ORIGINAL RAW SENSOR VALUES
       TO THE AI API

       IMPORTANT:
       The trained model expects these raw
       sensor values.
    ----------------------------------------- */

    sendSampleToAI({

        t1: t1,
        t2: t2,
        t3: t3,
        t4: t4,
        t5: t5,

        ax: rawAx,
        ay: rawAy,
        az: rawAz,

        gx: rawGx,
        gy: rawGy,
        gz: rawGz

    });

}


/* =========================================================
   SEND REAL SENSOR SAMPLE TO AI
========================================================= */

function sendSampleToAI(sample) {

    /*
       Put each request into a queue.

       This prevents multiple /predict requests
       from arriving out of order.
    */

    aiRequestQueue =
        aiRequestQueue.then(
            async function() {

                try {

                    const response =
                        await fetch(
                            AI_API_URL + "/predict",
                            {
                                method: "POST",

                                headers: {
                                    "Content-Type":
                                        "application/json"
                                },

                                body:
                                    JSON.stringify(sample)
                            }
                        );


                    if (!response.ok) {

                        throw new Error(
                            "AI API HTTP " +
                            response.status
                        );

                    }


                    const result =
                        await response.json();


                    aiAPIConnected = true;


                    if (
                        result.status ===
                        "BUFFERING"
                    ) {

                        document.getElementById(
                            "aiStatus"
                        ).textContent =
                            "Buffering";


                        document.getElementById(
                            "aiStatusText"
                        ).textContent =
                            "● " +
                            result.samples +
                            " / " +
                            result.required +
                            " samples";


                        document.getElementById(
                            "analysisModel"
                        ).textContent =
                            "BUFFERING";


                        return;

                    }


                    if (
                        result.status ===
                        "PREDICTED"
                    ) {

                        handleAIPrediction({

                            exercise:
                                result.prediction,

                            confidence:
                                result.confidence

                        });

                    }

                }

                catch (error) {

                    aiAPIConnected = false;


                    document.getElementById(
                        "analysisModel"
                    ).textContent =
                        "OFFLINE";


                    document.getElementById(
                        "aiStatus"
                    ).textContent =
                        "Offline";


                    document.getElementById(
                        "aiStatusText"
                    ).textContent =
                        "● Start the Python AI service";

                }

            }
        )
        .catch(
            function(error) {

                console.log(
                    "AI request queue error:",
                    error
                );

            }
        );

}


/* =========================================================
   CONNECT BUTTON
========================================================= */

const connectButton =
    document.createElement("button");


connectButton.textContent =
    "Connect Glove";


connectButton.className =
    "analysis-btn";


connectButton.style.marginTop =
    "10px";


connectButton.addEventListener(
    "click",
    async function() {

        await connectUSBSerial();

    }
);


const deviceDetails =
    document.querySelector(
        ".device-details"
    );


if (deviceDetails) {

    deviceDetails.appendChild(
        connectButton
    );

}


/* =========================================================
   EXERCISE SESSION BUTTON
========================================================= */

const startExerciseBtn =
    document.getElementById(
        "startExerciseBtn"
    );


if (startExerciseBtn) {

    startExerciseBtn.addEventListener(
        "click",
        function() {

            if (!sensorConnected) {

                alert(
                    "Please connect the GloveCare ESP8266 first."
                );

                return;

            }


            if (!aiAPIConnected) {

                alert(
                    "Please start the GloveCare AI Python service first."
                );

                return;

            }


            if (sessionRunning) {

                stopExerciseSession();

                return;

            }


            startExerciseSession();

        }
    );

}


/* =========================================================
   START SESSION
========================================================= */

async function startExerciseSession() {

    sessionRunning = true;

    sessionSeconds = 0;

    completedExercises = 0;

    currentExerciseIndex = 0;

    exerciseSeconds = 0;


    predictionHistory = [];

    matchingPredictionCount = 0;

    lastCompletedTime = 0;


    wristRollHistory = [];

    gyroMagnitudeHistory = [];


    currentSessionRecord = {

        id:
            Date.now(),

        date:
            new Date().toLocaleString(),

        duration:
            0,

        completed:
            0,

        total:
            5,

        status:
            "In Progress",

        feedback:
            "Session in progress"

    };


    await resetAIBuffer();


    startSessionTimer();

    startExerciseTimer();


    document.getElementById(
        "sessionStatus"
    ).textContent =
        "● Session running";


    document.getElementById(
        "exerciseCount"
    ).textContent =
        "0 / 5";


    document.getElementById(
        "currentExerciseStatus"
    ).textContent =
        "Listening";


    document.getElementById(
        "aiStatus"
    ).textContent =
        "Buffering";


    document.getElementById(
        "aiStatusText"
    ).textContent =
        "● Collecting real sensor samples";


    startExerciseBtn.innerHTML =
        "<span>■</span> Stop Exercise Session";


    updateCurrentExercise();


    renderSessionHistory();


    await playInstruction(
        currentExerciseIndex
    );

}


/* =========================================================
   RESET AI BUFFER
========================================================= */

async function resetAIBuffer() {

    try {

        await fetch(
            AI_API_URL + "/reset",
            {
                method: "POST"
            }
        );

    }

    catch (error) {

        console.log(
            "Could not reset AI buffer:",
            error
        );

    }

}


/* =========================================================
   STOP SESSION
========================================================= */

function stopExerciseSession() {

    sessionRunning = false;


    clearInterval(
        sessionTimer
    );


    clearInterval(
        exerciseTimer
    );


    stopAllAudio();


    predictionHistory = [];

    matchingPredictionCount = 0;

    wristRollHistory = [];

    gyroMagnitudeHistory = [];


    currentSessionRecord = null;


    startExerciseBtn.innerHTML =
        "<span>▶</span> Start Exercise Session";


    document.getElementById(
        "sessionStatus"
    ).textContent =
        "● Session stopped";


    document.getElementById(
        "currentExerciseStatus"
    ).textContent =
        "Stopped";


    document.getElementById(
        "aiStatus"
    ).textContent =
        "Ready";


    document.getElementById(
        "aiStatusText"
    ).textContent =
        "● AI monitoring ready";


    renderSessionHistory();

}


/* =========================================================
   SESSION TIMER
========================================================= */

function startSessionTimer() {

    clearInterval(
        sessionTimer
    );


    sessionTimer =
        setInterval(
            function() {

                if (!sessionRunning) {
                    return;
                }


                sessionSeconds++;


                document.getElementById(
                    "sessionTime"
                ).textContent =
                    formatTime(
                        sessionSeconds
                    );


                if (currentSessionRecord) {

                    currentSessionRecord.duration =
                        sessionSeconds;

                    currentSessionRecord.completed =
                        completedExercises;

                }

            },
            1000
        );

}


/* =========================================================
   EXERCISE TIMER
========================================================= */

function startExerciseTimer() {

    clearInterval(
        exerciseTimer
    );


    exerciseSeconds = 0;


    exerciseTimer =
        setInterval(
            function() {

                if (
                    !sessionRunning ||
                    currentExerciseIndex < 0
                ) {

                    return;

                }


                exerciseSeconds++;


                document.getElementById(
                    "currentExerciseTime"
                ).textContent =
                    formatTime(
                        exerciseSeconds
                    );

            },
            1000
        );

}


/* =========================================================
   TIME FORMAT
========================================================= */

function formatTime(totalSeconds) {

    const minutes =
        Math.floor(
            totalSeconds / 60
        );


    const seconds =
        totalSeconds % 60;


    return (
        String(minutes)
            .padStart(2, "0") +
        ":" +
        String(seconds)
            .padStart(2, "0")
    );

}


/* =========================================================
   CURRENT EXERCISE
========================================================= */

function updateCurrentExercise() {

    const exercise =
        exercises[
            currentExerciseIndex
        ];


    if (!exercise) {
        return;
    }


    document.getElementById(
        "currentExerciseName"
    ).textContent =
        exercise.name;


    document.getElementById(
        "currentExerciseInstruction"
    ).textContent =
        exercise.instruction;


    document.getElementById(
        "exerciseNumber"
    ).textContent =
        "Exercise " +
        (
            currentExerciseIndex + 1
        ) +
        " / 5";


    document.getElementById(
        "completedExercises"
    ).textContent =
        completedExercises +
        " / 5";


    const progress =
        Math.round(
            completedExercises /
            5 *
            100
        );


    document.getElementById(
        "exerciseProgressPercent"
    ).textContent =
        progress +
        "%";


    document.getElementById(
        "exerciseProgressBar"
    ).style.width =
        progress +
        "%";


    document.getElementById(
        "currentExerciseStatus"
    ).textContent =
        "Waiting for AI";


    exerciseSeconds = 0;


    document.getElementById(
        "currentExerciseTime"
    ).textContent =
        "00:00";


    predictionHistory = [];

    matchingPredictionCount = 0;

    wristRollHistory = [];

    gyroMagnitudeHistory = [];


    if (currentSessionRecord) {

        currentSessionRecord.completed =
            completedExercises;

    }

}


/* =========================================================
   AI SMOOTHING
========================================================= */

let predictionHistory = [];

let matchingPredictionCount = 0;

let lastCompletedTime = 0;


function getStablePrediction() {

    if (
        predictionHistory.length <
        STABLE_HISTORY_SIZE
    ) {

        return null;

    }


    const recentHistory =
        predictionHistory.slice(
            -STABLE_HISTORY_SIZE
        );


    const counts = {};


    recentHistory.forEach(
        item => {

            if (!counts[item.label]) {

                counts[item.label] =
                    0;

            }


            counts[item.label]++;

        }
    );


    let bestLabel = null;

    let bestCount = 0;


    Object.keys(counts).forEach(
        label => {

            if (
                counts[label] >
                bestCount
            ) {

                bestLabel =
                    label;

                bestCount =
                    counts[label];

            }

        }
    );


    if (!bestLabel) {
        return null;
    }


    const majority =
        bestCount /
        recentHistory.length;


    if (
        majority <
        REQUIRED_MAJORITY
    ) {

        return null;

    }


    const matching =
        recentHistory.filter(
            item =>
                item.label ===
                bestLabel
        );


    const averageConfidence =
        matching.reduce(
            (
                sum,
                item
            ) =>
                sum +
                item.confidence,
            0
        ) /
        matching.length;


    return {

        label:
            bestLabel,

        count:
            bestCount,

        majority:
            majority,

        confidence:
            averageConfidence

    };

}


/* =========================================================
   AI PREDICTION HANDLER
========================================================= */

window.handleAIPrediction =
    function(prediction) {

        if (!prediction) {
            return;
        }


        const predictedLabel =
            prediction.exercise ||
            prediction.label ||
            prediction.prediction ||
            "";


        if (!predictedLabel) {
            return;
        }


        let confidence =
            Number(
                prediction.confidence
            );


        if (Number.isNaN(confidence)) {
            confidence = 0;
        }


        if (confidence <= 1) {
            confidence *= 100;
        }


        confidence =
            Math.max(
                0,
                Math.min(
                    100,
                    confidence
                )
            );


        document.getElementById(
            "aiStatus"
        ).textContent =
            "Active";


        document.getElementById(
            "aiStatusText"
        ).textContent =
            "● Real-time AI prediction";


        document.getElementById(
            "analysisModel"
        ).textContent =
            "LIVE";


        document.getElementById(
            "aiScore"
        ).textContent =
            Math.round(
                confidence
            );


        const readableName =
            getReadableExerciseName(
                predictedLabel
            );


        document.getElementById(
            "predictionName"
        ).textContent =
            readableName;


        document.getElementById(
            "predictionText"
        ).textContent =
            "AI confidence: " +
            Math.round(
                confidence
            ) +
            "%";


        /* -----------------------------------------
           LOW CONFIDENCE FILTER
        ----------------------------------------- */

        if (
            confidence <
            MIN_CONFIDENCE
        ) {

            document.getElementById(
                "analysisExercise"
            ).textContent =
                "UNCERTAIN";


            document.getElementById(
                "currentExerciseStatus"
            ).textContent =
                "Low confidence";


            document.getElementById(
                "aiMessageTitle"
            ).textContent =
                "Movement not clear";


            document.getElementById(
                "aiMessageText"
            ).textContent =
                "The AI confidence is too low to confirm this movement.";


            /*
               IMPORTANT:
               Do NOT add low-confidence predictions
               to predictionHistory.
            */

            return;

        }


        /* -----------------------------------------
           NO ACTIVE SESSION
        ----------------------------------------- */

        if (!sessionRunning) {

            document.getElementById(
                "analysisExercise"
            ).textContent =
                "MONITORING";

            return;

        }


        /* -----------------------------------------
           ADD ONLY ACCEPTED PREDICTIONS
        ----------------------------------------- */

        predictionHistory.push({

            label:
                predictedLabel,

            confidence:
                confidence

        });


        if (
            predictionHistory.length >
            STABLE_HISTORY_SIZE
        ) {

            predictionHistory.shift();

        }


        const stable =
            getStablePrediction();


        if (!stable) {

            document.getElementById(
                "analysisExercise"
            ).textContent =
                "CHECK";


            document.getElementById(
                "currentExerciseStatus"
            ).textContent =
                "Checking movement";


            document.getElementById(
                "aiMessageTitle"
            ).textContent =
                "Checking movement";


            document.getElementById(
                "aiMessageText"
            ).textContent =
                "Waiting for several consistent sensor predictions.";


            return;

        }


        document.getElementById(
            "aiScore"
        ).textContent =
            Math.round(
                stable.confidence
            );


        const currentExercise =
            exercises[
                currentExerciseIndex
            ];


        if (!currentExercise) {
            return;
        }


        /* -----------------------------------------
           SPECIAL WRIST ROTATION LOGIC
        ----------------------------------------- */

        if (
            currentExercise.label ===
            "exercise_3_wrist_clockwise"
        ) {

            const strongWristMovement =
                hasStrongWristMovement();


            if (
                strongWristMovement
            ) {

                matchingPredictionCount++;


                document.getElementById(
                    "analysisExercise"
                ).textContent =
                    "MATCH";


                document.getElementById(
                    "currentExerciseStatus"
                ).textContent =
                    "Wrist movement detected";


                document.getElementById(
                    "aiMessageTitle"
                ).textContent =
                    "Wrist rotation detected";


                document.getElementById(
                    "aiMessageText"
                ).textContent =
                    "Strong wrist roll movement and gyro activity detected.";


                if (
                    matchingPredictionCount >=
                    REQUIRED_MATCHES &&
                    Date.now() -
                    lastCompletedTime >
                    4000
                ) {

                    completeCurrentExercise();

                }

                return;

            }


            /*
               If there is not enough wrist movement,
               do not complete the exercise even if
               the AI gives a weak wrist-rotation label.
            */

            matchingPredictionCount = 0;


            document.getElementById(
                "analysisExercise"
            ).textContent =
                "CHECK";


            document.getElementById(
                "currentExerciseStatus"
            ).textContent =
                "Rotate your wrist";


            document.getElementById(
                "aiMessageTitle"
            ).textContent =
                "Waiting for wrist movement";


            document.getElementById(
                "aiMessageText"
            ).textContent =
                "Continue rotating your wrist so the roll movement becomes clear.";


            return;

        }


        /* -----------------------------------------
           IDLE LOGIC
        ----------------------------------------- */

        if (
            currentExercise.label ===
            "idle"
        ) {

            const strongMovement =
                hasStrongWristMovement();


            if (
                strongMovement
            ) {

                matchingPredictionCount = 0;


                document.getElementById(
                    "analysisExercise"
                ).textContent =
                    "MOVING";


                document.getElementById(
                    "currentExerciseStatus"
                ).textContent =
                    "Keep hand still";


                document.getElementById(
                    "aiMessageTitle"
                ).textContent =
                    "Movement detected";


                document.getElementById(
                    "aiMessageText"
                ).textContent =
                    "Keep your hand relaxed and reduce wrist movement.";


                return;

            }

        }


        /* -----------------------------------------
           NORMAL EXERCISE MATCH
        ----------------------------------------- */

        if (
            stable.label ===
            currentExercise.label &&
            stable.confidence >=
            MIN_CONFIDENCE
        ) {

            matchingPredictionCount++;


            document.getElementById(
                "analysisExercise"
            ).textContent =
                "MATCH";


            document.getElementById(
                "currentExerciseStatus"
            ).textContent =
                "Detected";


            document.getElementById(
                "aiMessageTitle"
            ).textContent =
                "Exercise detected";


            document.getElementById(
                "aiMessageText"
            ).textContent =
                "The AI model consistently recognized the current exercise.";


            if (
                matchingPredictionCount >=
                REQUIRED_MATCHES &&
                Date.now() -
                lastCompletedTime >
                4000
            ) {

                completeCurrentExercise();

            }

        } else {

            matchingPredictionCount = 0;


            document.getElementById(
                "analysisExercise"
            ).textContent =
                "CHECK";


            document.getElementById(
                "currentExerciseStatus"
            ).textContent =
                "Keep going";


            document.getElementById(
                "aiMessageTitle"
            ).textContent =
                "Keep going";


            document.getElementById(
                "aiMessageText"
            ).textContent =
                "The detected movement does not yet match the current exercise.";

        }

    };


/* =========================================================
   LABEL → DISPLAY NAME
========================================================= */

function getReadableExerciseName(label) {

    const found =
        exercises.find(
            exercise =>
                exercise.label ===
                label
        );


    if (found) {
        return found.name;
    }


    if (label === "idle") {
        return "Idle";
    }


    return label
        .replaceAll("_", " ")
        .replace(
            /\b\w/g,
            letter =>
                letter.toUpperCase()
        );

}


/* =========================================================
   COMPLETE CURRENT EXERCISE
========================================================= */

async function completeCurrentExercise() {

    if (
        !sessionRunning ||
        currentExerciseIndex < 0
    ) {

        return;

    }


    lastCompletedTime =
        Date.now();


    completedExercises++;


    matchingPredictionCount = 0;

    predictionHistory = [];


    wristRollHistory = [];

    gyroMagnitudeHistory = [];


    if (currentSessionRecord) {

        currentSessionRecord.completed =
            completedExercises;

        currentSessionRecord.duration =
            sessionSeconds;

    }


    document.getElementById(
        "exerciseCount"
    ).textContent =
        completedExercises +
        " / 5";


    document.getElementById(
        "completedExercises"
    ).textContent =
        completedExercises +
        " / 5";


    const progress =
        Math.round(
            completedExercises /
            5 *
            100
        );


    document.getElementById(
        "exerciseProgressPercent"
    ).textContent =
        progress +
        "%";


    document.getElementById(
        "exerciseProgressBar"
    ).style.width =
        progress +
        "%";


    document.getElementById(
        "currentExerciseStatus"
    ).textContent =
        "Completed";


    document.getElementById(
        "aiMessageTitle"
    ).textContent =
        "Well done";


    document.getElementById(
        "aiMessageText"
    ).textContent =
        "Great work. Preparing the next exercise.";


    await playFeedback();


    await wait(700);


    if (
        completedExercises >= 5
    ) {

        finishExerciseSession();

        return;

    }


    currentExerciseIndex++;

    exerciseSeconds = 0;


    updateCurrentExercise();


    renderSessionHistory();


    await wait(300);


    if (sessionRunning) {

        await playInstruction(
            currentExerciseIndex
        );

    }

}


/* =========================================================
   FINISH SESSION
========================================================= */

function finishExerciseSession() {

    sessionRunning = false;


    clearInterval(
        sessionTimer
    );


    clearInterval(
        exerciseTimer
    );


    stopAllAudio();


    const completedSession = {

        id:
            currentSessionRecord
                ? currentSessionRecord.id
                : Date.now(),

        date:
            currentSessionRecord
                ? currentSessionRecord.date
                : new Date().toLocaleString(),

        duration:
            sessionSeconds,

        completed:
            5,

        total:
            5,

        status:
            "Completed",

        feedback:
            "Excellent! All 5 exercises were completed successfully."

    };


    saveCompletedSession(
        completedSession
    );


    currentSessionRecord =
        null;


    document.getElementById(
        "currentExerciseName"
    ).textContent =
        "Session Complete";


    document.getElementById(
        "currentExerciseInstruction"
    ).textContent =
        "All 5 exercises have been completed.";


    document.getElementById(
        "currentExerciseStatus"
    ).textContent =
        "Completed";


    document.getElementById(
        "sessionStatus"
    ).textContent =
        "● Session complete";


    document.getElementById(
        "aiStatus"
    ).textContent =
        "Complete";


    document.getElementById(
        "aiStatusText"
    ).textContent =
        "● Five exercises completed";


    document.getElementById(
        "analysisExercise"
    ).textContent =
        "COMPLETE";


    startExerciseBtn.innerHTML =
        "<span>✓</span> Session Complete";


    playFeedback();


    renderSessionHistory();

}


/* =========================================================
   SAVE COMPLETED SESSION
========================================================= */

function saveCompletedSession(session) {

    try {

        let history =
            JSON.parse(
                localStorage.getItem(
                    SESSION_HISTORY_KEY
                )
            );


        if (!Array.isArray(history)) {
            history = [];
        }


        history.unshift(session);


        localStorage.setItem(
            SESSION_HISTORY_KEY,
            JSON.stringify(history)
        );

    }

    catch (error) {

        console.log(
            "Could not save session history:",
            error
        );

    }

}


/* =========================================================
   GET SESSION HISTORY
========================================================= */

function getSessionHistory() {

    try {

        const history =
            JSON.parse(
                localStorage.getItem(
                    SESSION_HISTORY_KEY
                )
            );


        if (Array.isArray(history)) {
            return history;
        }


        return [];

    }

    catch (error) {

        console.log(
            "Could not read session history:",
            error
        );

        return [];

    }

}


/* =========================================================
   RENDER RECENT SESSIONS
========================================================= */

function renderSessionHistory() {

    const sessionList =
        document.querySelector(
            ".session-list"
        );


    if (!sessionList) {
        return;
    }


    const history =
        getSessionHistory();


    let html = "";


    if (currentSessionRecord) {

        const currentDuration =
            formatTime(
                currentSessionRecord.duration
            );


        html += `

            <div class="session-item">

                <div class="session-icon">
                    ●
                </div>

                <div class="session-info">

                    <strong>
                        Current Session
                    </strong>

                    <span>
                        ${currentSessionRecord.completed}
                        / 5 exercises completed
                        • ${currentDuration}
                    </span>

                </div>

                <div class="session-score">

                    <strong>
                        In Progress
                    </strong>

                    <span>
                        Live
                    </span>

                </div>

            </div>

        `;

    }


    history.forEach(
        session => {

            const duration =
                formatTime(
                    Number(
                        session.duration
                    ) || 0
                );


            html += `

                <div class="session-item">

                    <div class="session-icon">
                        ✓
                    </div>

                    <div class="session-info">

                        <strong>
                            Exercise Session
                        </strong>

                        <span>
                            ${session.date}
                            •
                            ${session.completed}/${session.total}
                            exercises
                            •
                            ${duration}
                        </span>

                        <span>
                            ${session.feedback}
                        </span>

                    </div>

                    <div class="session-score">

                        <strong>
                            Completed
                        </strong>

                        <span>
                            ${duration}
                        </span>

                    </div>

                </div>

            `;

        }
    );


    if (html === "") {

        html = `

            <div class="session-item">

                <div class="session-icon">
                    •
                </div>

                <div class="session-info">

                    <strong>
                        No completed sessions
                    </strong>

                    <span>
                        Your exercise sessions will appear here.
                    </span>

                </div>

                <div class="session-score">

                    <strong>
                        --
                    </strong>

                    <span>
                        Waiting
                    </span>

                </div>

            </div>

        `;

    }


    sessionList.innerHTML =
        html;

}


/* =========================================================
   LOAD HISTORY
========================================================= */

renderSessionHistory();


/* =========================================================
   NAVIGATION OBSERVER
========================================================= */

const sections =
    document.querySelectorAll(
        "#dashboard, #sensors, #exercises, #analysis, #history, #device, #settings"
    );


const observer =
    new IntersectionObserver(

        entries => {

            entries.forEach(
                entry => {

                    if (
                        entry.isIntersecting
                    ) {

                        const id =
                            entry.target.id;


                        navItems.forEach(
                            item => {

                                item.classList.remove(
                                    "active"
                                );


                                if (
                                    item.getAttribute(
                                        "href"
                                    ) ===
                                    "#" + id
                                ) {

                                    item.classList.add(
                                        "active"
                                    );

                                }

                            }
                        );

                    }

                }
            );

        },

        {
            threshold: 0.35
        }

    );


sections.forEach(
    section => {

        observer.observe(
            section
        );

    }
);


/* =========================================================
   SETTINGS
========================================================= */

const liveSensorToggle =
    document.getElementById(
        "liveSensorToggle"
    );


if (liveSensorToggle) {

    liveSensorToggle.addEventListener(
        "change",
        function() {

            if (!this.checked) {

                document.getElementById(
                    "liveSensorText"
                ).textContent =
                    "PAUSED";

            } else {

                document.getElementById(
                    "liveSensorText"
                ).textContent =
                    "LIVE";

            }

        }
    );

}


const aiMonitoringToggle =
    document.getElementById(
        "aiMonitoringToggle"
    );


if (aiMonitoringToggle) {

    aiMonitoringToggle.addEventListener(
        "change",
        function() {

            if (this.checked) {

                document.getElementById(
                    "aiStatusText"
                ).textContent =
                    "● AI monitoring enabled";

            } else {

                document.getElementById(
                    "aiStatusText"
                ).textContent =
                    "● AI monitoring disabled";

            }

        }
    );

}
