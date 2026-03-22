// ========== GAME MODULE ==========

let canvas, ctx;
let tiles = [];
let rows = 3;
let tileSize;
let draggingTile = null;
let offsetX = 0, offsetY = 0;
let img = new Image();
let activeGame = null;
let hasResizeListener = false;
const PUZZLE_CANVAS_SIZE = 500;
const sourceCanvas = document.createElement("canvas");
const sourceCtx = sourceCanvas.getContext("2d");
let imageReady = false;
let moves = 0;
let elapsedSeconds = 0;
let timerId = null;
let gameWon = false;
let uploadedImageUrl = null;
let breathingTimerId = null;

img.src = "/static/bg1.jpg";
img.onload = () => {
    imageReady = img.naturalWidth > 0;
};
img.onerror = () => {
    imageReady = false;
};
let selectedGame = null;

// INIT after DOM loads
window.addEventListener("load", () => {
    canvas = document.getElementById("gameCanvas");
    if (!canvas) return;

    ctx = canvas.getContext("2d");

    canvas.addEventListener("mousedown", onMouseDown);
    canvas.addEventListener("mousemove", onMouseMove);
    canvas.addEventListener("mouseup", onMouseUp);

    const puzzleImageInput = document.getElementById("puzzleImageInput");
    if (puzzleImageInput) {
        puzzleImageInput.addEventListener("change", onPuzzleImageSelected);
    }

    const completionInput = document.getElementById("completionInput");
    if (completionInput) {
        completionInput.addEventListener("keydown", onCompletionInputKeydown);
    }
});

//SWITCHING
function showGameView() {
    document.getElementById("chatView").style.display = "none";
    document.getElementById("gameContainer").style.display = "block";
    document.getElementById("gameStage").style.display = "none";
    document.getElementById("gameMenu").style.display = "flex";
    document.getElementById("difficultyMenu").style.display = "none";
    document.getElementById("gameCanvas").style.display = "none";
    stopTimer();
    resetCompletionFlow();
    setTimeout(() => {
        resizeCanvas();
        draw();
    }, 50);
}

function showChatView() {
    document.getElementById("chatView").style.display = "flex";
    document.getElementById("gameContainer").style.display = "none";
    stopTimer();
    activeGame = null;
    resetCompletionFlow();
}

function startGame(r) {
    document.getElementById("gameStage").style.display = "flex";
    document.getElementById("gameMenu").style.display = "none";
    document.getElementById("difficultyMenu").style.display = "none";
    document.getElementById("gameCanvas").style.display = "block";
    rows = r;
    activeGame = "puzzle";
    gameWon = false;
    moves = 0;
    elapsedSeconds = 0;
    updateHud();
    startTimer();
    resetCompletionFlow();

    if (!canvas) {
        canvas = document.getElementById("gameCanvas");
        ctx = canvas.getContext("2d");
    }

    if (!hasResizeListener) {
        window.addEventListener("resize", () => {
            resizeCanvas();
            if (activeGame === "puzzle" && tiles.length) {
                draw();
            }
        });
        hasResizeListener = true;
    }

    resizeCanvas();

    tileSize = canvas.width / rows;
    tiles = [];

    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < rows; c++) {
            tiles.push({
                sx: c * tileSize,
                sy: r * tileSize,
                x: c * tileSize,
                y: r * tileSize
            });
        }
    }

    shuffle();
    draw();
    updateScore();
}

function shuffle() {
    tiles.sort(() => Math.random() - 0.5);

    tiles.forEach((t, i) => {
        t.x = (i % rows) * tileSize;
        t.y = Math.floor(i / rows) * tileSize;
    });
}

function draw() {
    if (activeGame !== "puzzle") return;   
    if (!canvas || !ctx || !tiles.length) return;

    const source = getPuzzleSource();
    if (!source) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    tiles.forEach(tile => {
        ctx.drawImage(
            source,
            tile.sx, tile.sy, tileSize, tileSize,
            tile.x, tile.y, tileSize, tileSize
        );
    });
}

function getPuzzleSource() {
    if (imageReady && img.complete && img.naturalWidth > 0) {
        if (!canvas || !sourceCtx) return img;

        sourceCanvas.width = canvas.width;
        sourceCanvas.height = canvas.height;

        const srcW = img.naturalWidth;
        const srcH = img.naturalHeight;
        const srcSize = Math.min(srcW, srcH);
        const sx = Math.floor((srcW - srcSize) / 2);
        const sy = Math.floor((srcH - srcSize) / 2);

        sourceCtx.clearRect(0, 0, sourceCanvas.width, sourceCanvas.height);
        sourceCtx.drawImage(
            img,
            sx,
            sy,
            srcSize,
            srcSize,
            0,
            0,
            sourceCanvas.width,
            sourceCanvas.height
        );
        return sourceCanvas;
    }

    if (!canvas || !sourceCtx) return null;

    sourceCanvas.width = canvas.width;
    sourceCanvas.height = canvas.height;

    const grad = sourceCtx.createLinearGradient(0, 0, sourceCanvas.width, sourceCanvas.height);
    grad.addColorStop(0, "#667eea");
    grad.addColorStop(1, "#764ba2");
    sourceCtx.fillStyle = grad;
    sourceCtx.fillRect(0, 0, sourceCanvas.width, sourceCanvas.height);

    sourceCtx.fillStyle = "rgba(255,255,255,0.18)";
    for (let i = 0; i < sourceCanvas.width; i += 24) {
        sourceCtx.fillRect(i, 0, 1, sourceCanvas.height);
        sourceCtx.fillRect(0, i, sourceCanvas.width, 1);
    }

    sourceCtx.fillStyle = "white";
    sourceCtx.font = `bold ${Math.floor(sourceCanvas.width / 9)}px Segoe UI`;
    sourceCtx.textAlign = "center";
    sourceCtx.textBaseline = "middle";
    sourceCtx.fillText("PUZZLE", sourceCanvas.width / 2, sourceCanvas.height / 2);

    return sourceCanvas;
}

// ================= MOUSE =================

function onMouseDown(e) {
    let x = e.offsetX;
    let y = e.offsetY;

    draggingTile = tiles.find(t =>
        x > t.x && x < t.x + tileSize &&
        y > t.y && y < t.y + tileSize
    );

    if (draggingTile) {
        offsetX = draggingTile.x - x;
        offsetY = draggingTile.y - y;
    }
}

function onMouseMove(e) {
    if (draggingTile) {
        draggingTile.x = e.offsetX + offsetX;
        draggingTile.y = e.offsetY + offsetY;
        draw();
    }
}

function onMouseUp() {
    if (!draggingTile) return;

    let gx = Math.round(draggingTile.x / tileSize);
    let gy = Math.round(draggingTile.y / tileSize);

    gx = Math.max(0, Math.min(rows - 1, gx));
    gy = Math.max(0, Math.min(rows - 1, gy));

    let targetX = gx * tileSize;
    let targetY = gy * tileSize;

    let other = tiles.find(t => t.x === targetX && t.y === targetY);

    if (other && other !== draggingTile) {
        [other.x, draggingTile.x] = [draggingTile.x, other.x];
        [other.y, draggingTile.y] = [draggingTile.y, other.y];
    } else {
        draggingTile.x = targetX;
        draggingTile.y = targetY;
    }

    draggingTile = null;
    moves += 1;
    updateScore();
    draw();
}

function resizeCanvas() {
    const localCanvas = document.getElementById("gameCanvas");
    if (!localCanvas) return;

    localCanvas.style.width = `${PUZZLE_CANVAS_SIZE}px`;
    localCanvas.style.height = `${PUZZLE_CANVAS_SIZE}px`;
    localCanvas.width = PUZZLE_CANVAS_SIZE;
    localCanvas.height = PUZZLE_CANVAS_SIZE;
}

function selectGame(type) {
    selectedGame = type;
    console.log("Selected Game:", type);

    document.getElementById("gameMenu").style.display = "none";
    document.getElementById("gameStage").style.display = "none";
    resetCompletionFlow();

    document.getElementById("difficultyMenu").style.display = "flex";
}

function updateHud() {
    const scoreEl = document.getElementById("scoreValue");
    const timeEl = document.getElementById("timeValue");
    if (scoreEl) scoreEl.textContent = String(moves);
    if (timeEl) timeEl.textContent = formatTime(elapsedSeconds);
}

function formatTime(totalSeconds) {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

function startTimer() {
    stopTimer();
    timerId = setInterval(() => {
        elapsedSeconds += 1;
        updateHud();
    }, 1000);
}

function stopTimer() {
    if (timerId) {
        clearInterval(timerId);
        timerId = null;
    }
}

function updateScore() {
    updateHud();

    if (gameWon || !tiles.length) return;
    const isSolved = tiles.every(tile => tile.x === tile.sx && tile.y === tile.sy);
    if (isSolved) {
        gameWon = true;
        stopTimer();
        showPostPuzzleFlow();
    }
}

function backToGameMenu() {
    stopTimer();
    activeGame = null;
    draggingTile = null;
    tiles = [];
    moves = 0;
    elapsedSeconds = 0;
    gameWon = false;
    updateHud();
    resetCompletionFlow();

    document.getElementById("gameCanvas").style.display = "none";
    document.getElementById("difficultyMenu").style.display = "none";
    document.getElementById("gameStage").style.display = "none";
    document.getElementById("gameMenu").style.display = "flex";

    if (canvas && ctx) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
}

function resetCompletionFlow() {
    const completionScreen = document.getElementById("completionScreen");
    const gameHud = document.getElementById("gameHud");
    const gameBoardRow = document.querySelector(".gameBoardRow");
    const completionTitle = document.getElementById("completionTitle");
    const breathingText = document.getElementById("breathingText");
    const breathingCountdown = document.getElementById("breathingCountdown");
    const completionPrompt = document.getElementById("completionPrompt");
    const completionInput = document.getElementById("completionInput");

    if (breathingTimerId) {
        clearInterval(breathingTimerId);
        breathingTimerId = null;
    }

    if (gameHud) gameHud.style.display = "flex";
    if (gameBoardRow) gameBoardRow.style.display = "flex";
    if (completionScreen) completionScreen.style.display = "none";
    if (completionTitle) completionTitle.textContent = "Great job!";
    if (breathingText) breathingText.textContent = "Breathe slowly for 10 seconds";
    if (breathingCountdown) {
        breathingCountdown.style.display = "block";
        breathingCountdown.textContent = "10";
    }
    if (completionPrompt) completionPrompt.style.display = "none";
    if (completionInput) {
        completionInput.style.display = "none";
        completionInput.value = "";
    }
}

function showPostPuzzleFlow() {
    const completionScreen = document.getElementById("completionScreen");
    const gameHud = document.getElementById("gameHud");
    const gameBoardRow = document.querySelector(".gameBoardRow");
    const completionTitle = document.getElementById("completionTitle");
    const breathingText = document.getElementById("breathingText");
    const breathingCountdown = document.getElementById("breathingCountdown");
    const completionPrompt = document.getElementById("completionPrompt");
    const completionInput = document.getElementById("completionInput");
    if (!completionScreen || !completionTitle || !breathingText || !breathingCountdown || !completionPrompt || !completionInput) return;

    if (gameHud) gameHud.style.display = "none";
    if (gameBoardRow) gameBoardRow.style.display = "none";
    completionScreen.style.display = "flex";
    completionTitle.textContent = `Great job! You solved it in ${moves} moves and ${formatTime(elapsedSeconds)}.`;

    let remaining = 10;
    breathingText.textContent = "Breathe slowly";
    breathingCountdown.style.display = "block";
    breathingCountdown.textContent = String(remaining);
    completionPrompt.style.display = "none";
    completionInput.style.display = "none";
    completionInput.value = "";

    if (breathingTimerId) {
        clearInterval(breathingTimerId);
    }

    breathingTimerId = setInterval(() => {
        remaining -= 1;
        if (remaining > 0) {
            breathingCountdown.textContent = String(remaining);
            return;
        }

        clearInterval(breathingTimerId);
        breathingTimerId = null;
        breathingText.textContent = "Nice.";
        breathingCountdown.style.display = "none";
        completionPrompt.style.display = "block";
        completionInput.style.display = "block";
        completionInput.focus();
    }, 1000);
}

function onCompletionInputKeydown(event) {
    if (event.key !== "Enter") return;
    event.preventDefault();

    const completionInput = document.getElementById("completionInput");
    const completionPrompt = document.getElementById("completionPrompt");
    if (completionInput) completionInput.style.display = "none";
    if (completionPrompt) completionPrompt.style.display = "none";

    goToDifficultyMenu();
}

function goToDifficultyMenu() {
    stopTimer();
    activeGame = null;
    draggingTile = null;
    tiles = [];
    gameWon = false;
    moves = 0;
    elapsedSeconds = 0;
    updateHud();
    resetCompletionFlow();

    const canvasEl = document.getElementById("gameCanvas");
    const gameStage = document.getElementById("gameStage");
    const gameMenu = document.getElementById("gameMenu");
    const difficultyMenu = document.getElementById("difficultyMenu");

    if (canvasEl) canvasEl.style.display = "none";
    if (gameStage) gameStage.style.display = "none";
    if (gameMenu) gameMenu.style.display = "none";
    if (difficultyMenu) difficultyMenu.style.display = "flex";

    if (canvas && ctx) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
}

function triggerPuzzleImageUpload() {
    const puzzleImageInput = document.getElementById("puzzleImageInput");
    if (puzzleImageInput) {
        puzzleImageInput.click();
    }
}

function onPuzzleImageSelected(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    if (uploadedImageUrl) {
        URL.revokeObjectURL(uploadedImageUrl);
    }
    uploadedImageUrl = URL.createObjectURL(file);

    const referenceImage = document.getElementById("referenceImage");
    if (referenceImage) {
        referenceImage.src = uploadedImageUrl;
    }

    imageReady = false;
    img.onload = () => {
        imageReady = img.naturalWidth > 0;
        if (activeGame === "puzzle" && tiles.length) {
            draw();
        }
    };
    img.onerror = () => {
        imageReady = false;
        alert("Could not load image. Please try another file.");
    };
    img.src = uploadedImageUrl;

    if (activeGame === "puzzle") {
        startGame(rows);
    }
}
function startSelectedGame(level) {
    let size;
    console.log("Starting:", selectedGame);
    if (level === "easy") size = 3;
    else if (level === "medium") size = 4;
    else size = 5;

    if (selectedGame === "arrange") {
        startArrangeGame(size);
    } else {
        startGame(size);
    }
}