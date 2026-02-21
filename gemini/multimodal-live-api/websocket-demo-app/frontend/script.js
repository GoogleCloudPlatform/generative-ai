window.addEventListener("load", (event) => {
    console.log("Hello Gemini Realtime Demo!");

    setAvailableCamerasOptions();
    setAvailableMicrophoneOptions();
});

const PROXY_URL = "ws://localhost:8080";
// const PROXY_URL = "/ws";
const PROJECT_ID = "visionai-testing-stable";
// const MODEL = "gemini-2.0-flash-exp";
// const MODEL = "gemini-2.0-flash-live-preview-04-09";
// const MODEL = "gemini-2.5-flash-preview-native-audio";
const MODEL = "gemini-live-2.5-flash-preview-native-audio";
// const MODEL = "gemini-2.5-flash-preview-native-audio-dialog";
const API_HOST = "us-central1-aiplatform.googleapis.com";
// const API_HOST = "us-central1-autopush-aiplatform.sandbox.googleapis.com";
// const API_HOST = "us-central1-staging-aiplatform.sandbox.googleapis.com";
const accessTokenInput = document.getElementById("token");
const projectInput = document.getElementById("project");
const systemInstructionsInput = document.getElementById("systemInstructions");

CookieJar.init("token");
CookieJar.init("project");
CookieJar.init("systemInstructions");

const disconnected = document.getElementById("disconnected");
const connecting = document.getElementById("connecting");
const connected = document.getElementById("connected");
const speaking = document.getElementById("speaking");

const micBtn = document.getElementById("micBtn");
const micOffBtn = document.getElementById("micOffBtn");
const cameraBtn = document.getElementById("cameraBtn");
const cameraOffBtn = document.getElementById("cameraOffBtn");
const screenBtn = document.getElementById("screenBtn");

const cameraSelect = document.getElementById("cameraSource");
const micSelect = document.getElementById("audioSource");

const envApiHost = document.getElementById("envApiHost");
const inputTranscript = document.getElementById("inputTranscript");
const outputTranscript = document.getElementById("outputTranscript");
const enableResumption = document.getElementById("resumption");
const resumptionHandle = document.getElementById("handle");
const voiceName = document.getElementById("voiceName");
const voiceLocale = document.getElementById("voiceLocale");
const disableInterruption = document.getElementById("disableInterruption");
const disableDetection = document.getElementById("disableDetection");
const startSensitivity = document.getElementById("startSensitivity");
const endSensitivity = document.getElementById("endSensitivity");

const proactiveVideo = document.getElementById("proactiveVideo");
const audioInterval = document.getElementById("audioInterval");
const videoInterval = document.getElementById("videoInterval");


const geminiLiveApi = new GeminiLiveAPI(PROXY_URL, PROJECT_ID, MODEL, API_HOST);

geminiLiveApi.onErrorMessage = (message) => {
    showDialogWithMessage(message);
    setAppStatus("disconnected");
};

function getSelectedResponseModality() {
    const radioButtons = document.querySelectorAll(
        'md-radio[name="responseModality"]',
    );

    let selectedValue;
    for (const radioButton of radioButtons) {
        if (radioButton.checked) {
            selectedValue = radioButton.value;
            break;
        }
    }
    return selectedValue;
}

function getSystemInstructions() {
    return systemInstructionsInput.value;
}

function getApiHost() {
    if (envApiHost.value === 'autopush') {
        return 'us-central1-autopush-aiplatform.sandbox.googleapis.com'
    }
    if (envApiHost.value === 'staging') {
        return 'us-central1-staging-aiplatform.sandbox.googleapis.com'
    }
    return 'us-central1-aiplatform.googleapis.com'
}

function connectBtnClick() {
    setAppStatus("connecting");

    geminiLiveApi.responseModalities = getSelectedResponseModality();
    if (getSystemInstructions() !== "") {
        geminiLiveApi.systemInstructions = getSystemInstructions();
    }
    geminiLiveApi.setApiHost(getApiHost());
    geminiLiveApi.setTranscript(inputTranscript.checked, outputTranscript.checked);
    geminiLiveApi.setResumption(enableResumption.checked, resumptionHandle.value);
    geminiLiveApi.setVoice(voiceName.value, voiceLocale.value);
    geminiLiveApi.setVad(disableInterruption.checked, disableDetection.checked,
        startSensitivity.value, endSensitivity.value
    );
    geminiLiveApi.setProactiveVideo(proactiveVideo.checked);


    geminiLiveApi.onConnectionStarted = () => {
        setAppStatus("connected");
        // startAudioInput();
    };

    geminiLiveApi.setProjectId(projectInput.value);
    geminiLiveApi.connect(accessTokenInput.value);

}

const liveAudioOutputManager = new LiveAudioOutputManager();

geminiLiveApi.onReceiveResponse = (messageResponse) => {
    console.log("message response type: " + messageResponse.type);
    if (messageResponse.type === "AUDIO") {
        liveAudioOutputManager.playAudioChunk(messageResponse.data);
    } else if (messageResponse.type === "TEXT") {
        console.log("Gemini said: ", messageResponse.data);
        newModelMessage(messageResponse.data);
    } else if (messageResponse.type === "RESUMPTION") {
        console.log("Resumption handle received: ", messageResponse.data);
        newModelMessage("New Resumption Handle ID: " + messageResponse.data);
    } else if (messageResponse.type === "INPUT_TRANSCRIPTION") {
        console.log("Input transcription received: ", messageResponse.data);
        newModelMessage("Input Transcription: " + messageResponse.data);
    } else if (messageResponse.type === "OUTPUT_TRANSCRIPTION") {
        console.log("Output transcription received: ", messageResponse.data);
        newModelMessage("Output Transcription: " + messageResponse.data);
    } else if (messageResponse.type === "END_OF_TURN") {
        console.log("End of turn");
        newModelMessage("End of turn!");
    } else if (messageResponse.type === "INTERRUPT") {
        console.log("Interrupted!");
        newModelMessage("Interrupted!");
    } else if (messageResponse.type === "VAD_SIGNAL") {
        console.log("VAD signal");
        newModelMessage("VAD signal received");
    }
};

const liveAudioInputManager = new LiveAudioInputManager();

liveAudioInputManager.onNewAudioRecordingChunk = (audioData) => {
    geminiLiveApi.sendAudioMessage(audioData);
};

function addMessageToChat(message) {
    const textChat = document.getElementById("text-chat");
    const newParagraph = document.createElement("p");
    newParagraph.textContent = message;
    textChat.appendChild(newParagraph);
}

function newModelMessage(message) {
    addMessageToChat(">> " + message);
}

function newUserMessage() {
    const textMessage = document.getElementById("text-message");
    addMessageToChat("User: " + textMessage.value);
    geminiLiveApi.sendTextMessage(textMessage.value);

    textMessage.value = "";
}

function startAudioInput() {
    liveAudioInputManager.updateAudioInterval(audioInterval.value);
}

function stopAudioInput() {
    liveAudioInputManager.disconnectMicrophone();
}

function micBtnClick() {
    console.log("micBtnClick");
    stopAudioInput();
    micBtn.hidden = true;
    micOffBtn.hidden = false;
}

function micOffBtnClick() {
    console.log("micOffBtnClick");
    startAudioInput();

    micBtn.hidden = false;
    micOffBtn.hidden = true;
}

function audioStartButtonClick() {
    console.log("start voice activity...");
    geminiLiveApi.sendVoiceActivityMessage(true);
}

function audioEndButtonClick() {
    console.log("end voice activity...");
    geminiLiveApi.sendVoiceActivityMessage(false);
}

const videoElement = document.getElementById("video");
const canvasElement = document.getElementById("canvas");

const liveVideoManager = new LiveVideoManager(videoElement, canvasElement);

const liveScreenManager = new LiveScreenManager(videoElement, canvasElement);

liveVideoManager.onNewFrame = (b64Image) => {
    geminiLiveApi.sendImageMessage(b64Image);
};

liveScreenManager.onNewFrame = (b64Image) => {
    geminiLiveApi.sendImageMessage(b64Image);
};

function startCameraCapture() {
    liveScreenManager.stopCapture();
    liveVideoManager.updateVideoInterval(videoInterval.value);
    // liveVideoManager.startWebcam();
}

function startScreenCapture() {
    liveVideoManager.stopWebcam();
    liveScreenManager.updateVideoInterval(videoInterval.value);
    // liveScreenManager.startCapture();
}

function cameraBtnClick() {
    liveVideoManager.stopWebcam();
    cameraBtn.hidden = true;
    cameraOffBtn.hidden = false;
    console.log("Camera turned off");
}

function cameraOffBtnClick() {
    startCameraCapture();
    cameraBtn.hidden = false;
    cameraOffBtn.hidden = true;
    console.log("Camera turned on");
}

function screenShareBtnClick() {
    startScreenCapture();
    console.log("screenShareBtnClick");
}

function newCameraSelected() {
    console.log("newCameraSelected ", cameraSelect.value);
    liveVideoManager.updateWebcamDevice(cameraSelect.value);
}

function newMicSelected() {
    console.log("newMicSelected", micSelect.value);
    liveAudioInputManager.updateMicrophoneDevice(micSelect.value);
}

function disconnectBtnClick() {
    setAppStatus("disconnected");
    geminiLiveApi.disconnect();
    stopAudioInput();
}

function showDialogWithMessage(messageText) {
    const dialog = document.getElementById("dialog");
    const dialogMessage = document.getElementById("dialogMessage");
    dialogMessage.innerHTML = messageText;
    dialog.show();
}

async function getAvailableDevices(deviceType) {
    const allDevices = await navigator.mediaDevices.enumerateDevices();
    const devices = [];
    allDevices.forEach((device) => {
        if (device.kind === deviceType) {
            devices.push({
                id: device.deviceId,
                name: device.label || device.deviceId,
            });
        }
    });
    return devices;
}

async function getAvailableCameras() {
    return await this.getAvailableDevices("videoinput");
}

async function getAvailableAudioInputs() {
    return await this.getAvailableDevices("audioinput");
}

function setMaterialSelect(allOptions, selectElement) {
    allOptions.forEach((optionData) => {
        const option = document.createElement("md-select-option");
        option.value = optionData.id;

        const slotDiv = document.createElement("div");
        slotDiv.slot = "headline";
        slotDiv.innerHTML = optionData.name;
        option.appendChild(slotDiv);

        selectElement.appendChild(option);
    });
}

async function setAvailableCamerasOptions() {
    const cameras = await getAvailableCameras();
    const videoSelect = document.getElementById("cameraSource");
    setMaterialSelect(cameras, videoSelect);
}

async function setAvailableMicrophoneOptions() {
    const mics = await getAvailableAudioInputs();
    const audioSelect = document.getElementById("audioSource");
    setMaterialSelect(mics, audioSelect);
}

function setAppStatus(status) {
    disconnected.hidden = true;
    connecting.hidden = true;
    connected.hidden = true;
    speaking.hidden = true;

    switch (status) {
        case "disconnected":
            disconnected.hidden = false;
            break;
        case "connecting":
            connecting.hidden = false;
            break;
        case "connected":
            connected.hidden = false;
            break;
        case "speaking":
            speaking.hidden = false;
            break;
        default:
    }
}
