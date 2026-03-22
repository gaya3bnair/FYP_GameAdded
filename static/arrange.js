// ========== ARRANGE (SLIDING PUZZLE) GAME ==========

let arrangeBoard = [];
let arrangeSize = 4;
let arrangeMoves = 0;
let arrangeWon = false;

function startArrangeGame(size) {
    arrangeSize = size;
    arrangeMoves = 0;
    arrangeWon = false;

    activeGame = "arrange";

    document.getElementById("gameStage").style.display = "flex";
    document.getElementById("gameMenu").style.display = "none";
    document.getElementById("difficultyMenu").style.display = "none";
    document.getElementById("gameCanvas").style.display = "block";

    // 🔴 STOP PUZZLE GAME COMPLETELY
    tiles = [];              // remove puzzle tiles
    draggingTile = null;     // stop drag logic

    resizeCanvas();
    initArrangeBoard();

    // clear canvas before drawing
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    drawArrange();
    startTimer();
}

function initArrangeBoard() {
    arrangeBoard = [];

    for (let i = 1; i < arrangeSize * arrangeSize; i++) {
        arrangeBoard.push(i);
    }
    arrangeBoard.push(0);

    shuffleArrange();
}

function shuffleArrange() {
    do {
        arrangeBoard.sort(() => Math.random() - 0.5);
    } while (!isSolvable(arrangeBoard) || isSolved());
}

function isSolvable(board) {
    let inv = 0;

    for (let i = 0; i < board.length; i++) {
        for (let j = i + 1; j < board.length; j++) {
            if (board[i] && board[j] && board[i] > board[j]) inv++;
        }
    }

    if (arrangeSize % 2 === 1) return inv % 2 === 0;

    let emptyRow = Math.floor(board.indexOf(0) / arrangeSize);
    return (inv + emptyRow) % 2 === 1;
}

function drawArrange() {
    if (!canvas || !ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    let size = canvas.width / arrangeSize;

    arrangeBoard.forEach((val, i) => {
        let x = (i % arrangeSize) * size;
        let y = Math.floor(i / arrangeSize) * size;

        ctx.fillStyle = val === 0 ? "#c8cdd2" : "#78aaff";
        ctx.fillRect(x + 5, y + 5, size - 10, size - 10);

        if (val !== 0) {
            ctx.fillStyle = "white";
            ctx.font = `${size / 3}px Segoe UI`;
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(val, x + size / 2, y + size / 2);
        }
    });
}

canvas?.addEventListener("click", (e) => {
    if (activeGame !== "arrange") return;

    let rect = canvas.getBoundingClientRect();
    let x = e.clientX - rect.left;
    let y = e.clientY - rect.top;

    let size = canvas.width / arrangeSize;

    let col = Math.floor(x / size);
    let row = Math.floor(y / size);
    let index = row * arrangeSize + col;

    moveArrangeTile(index);
});

function moveArrangeTile(index) {
    let empty = arrangeBoard.indexOf(0);

    let r1 = Math.floor(index / arrangeSize);
    let c1 = index % arrangeSize;

    let r2 = Math.floor(empty / arrangeSize);
    let c2 = empty % arrangeSize;

    if (Math.abs(r1 - r2) + Math.abs(c1 - c2) === 1) {
        [arrangeBoard[index], arrangeBoard[empty]] =
            [arrangeBoard[empty], arrangeBoard[index]];

        arrangeMoves++;
        updateHud();
        drawArrange();

        if (isSolved()) {
            arrangeWon = true;
            stopTimer();
            showPostPuzzleFlow();
        }
    }
}

function isSolved() {
    for (let i = 0; i < arrangeBoard.length - 1; i++) {
        if (arrangeBoard[i] !== i + 1) return false;
    }
    return arrangeBoard[arrangeBoard.length - 1] === 0;
}