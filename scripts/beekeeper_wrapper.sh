#!/bin/bash
# beekeeperコマンドラッパー - 全ての指示をDBに保存
# beekeeperからの指示を自動的に傍受してデータベースに記録

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# デフォルト設定
HIVE_DB_PATH="${PROJECT_ROOT}/hive/hive_memory.db"
SESSION_NAME="beehive"
DEFAULT_TARGET="all"

# 使用方法表示
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] "INSTRUCTION"

Options:
    -t, --target BEE_NAME    Target bee (default: all)
    -p, --priority LEVEL     Priority level (low/normal/high/urgent, default: normal)
    -h, --help               Show this help message

Examples:
    $0 "issue 47を実装してください"
    $0 --target developer "バグを修正してください"
    $0 --priority high "緊急でテストを実行してください"

Environment Variables:
    HIVE_DB_PATH            Path to hive database (default: $HIVE_DB_PATH)
    BEEHIVE_SESSION         tmux session name (default: $SESSION_NAME)
EOF
}

# パラメータ解析
TARGET="$DEFAULT_TARGET"
PRIORITY="normal"
INSTRUCTION=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--target)
            TARGET="$2"
            shift 2
            ;;
        -p|--priority)
            PRIORITY="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        -*)
            echo "Unknown option: $1" >&2
            show_usage
            exit 1
            ;;
        *)
            if [[ -z "$INSTRUCTION" ]]; then
                INSTRUCTION="$1"
            else
                echo "Multiple instructions not supported" >&2
                exit 1
            fi
            shift
            ;;
    esac
done

# 指示が指定されているかチェック
if [[ -z "$INSTRUCTION" ]]; then
    echo "Error: No instruction provided" >&2
    show_usage
    exit 1
fi

# 環境変数から設定を取得
HIVE_DB_PATH="${HIVE_DB_PATH:-$PROJECT_ROOT/hive/hive_memory.db}"
SESSION_NAME="${BEEHIVE_SESSION:-beehive}"

# データベース存在チェック
if [[ ! -f "$HIVE_DB_PATH" ]]; then
    echo "Error: Hive database not found at $HIVE_DB_PATH" >&2
    echo "Please run 'sqlite3 \"$HIVE_DB_PATH\" < hive/schema.sql' to initialize" >&2
    exit 1
fi

# 有効なbee名リスト
VALID_BEES=("all" "queen" "developer" "qa" "analyst")

# ターゲットbeeの検証
if [[ "$TARGET" != "all" ]]; then
    VALID=false
    for bee in "${VALID_BEES[@]}"; do
        if [[ "$TARGET" == "$bee" ]]; then
            VALID=true
            break
        fi
    done
    
    if [[ "$VALID" != "true" ]]; then
        echo "Error: Invalid target bee '$TARGET'" >&2
        echo "Valid targets: ${VALID_BEES[*]}" >&2
        exit 1
    fi
fi

# 優先度の検証
case "$PRIORITY" in
    low|normal|high|urgent)
        ;;
    *)
        echo "Error: Invalid priority '$PRIORITY'" >&2
        echo "Valid priorities: low, normal, high, urgent" >&2
        exit 1
        ;;
esac

# ログ関数
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
}

log_info "Beekeeper instruction intercepted"
log_info "Target: $TARGET, Priority: $PRIORITY"
log_info "Instruction: ${INSTRUCTION:0:50}..."

# Pythonの会話デーモンを使用して指示を傍受
cd "$PROJECT_ROOT"

# 会話デーモン経由で指示を処理
python3 scripts/conversation_daemon.py \
    --intercept "$INSTRUCTION" \
    --target "$TARGET" 2>/dev/null

DAEMON_EXIT_CODE=$?

if [[ $DAEMON_EXIT_CODE -eq 0 ]]; then
    log_info "Instruction successfully logged to database"
else
    log_error "Failed to log instruction via daemon (exit code: $DAEMON_EXIT_CODE)"
    
    # フォールバック: 直接SQLiteに記録
    log_info "Attempting fallback SQLite logging..."
    
    # UUIDベースの会話ID生成
    if command -v uuidgen >/dev/null 2>&1; then
        CONVERSATION_ID=$(uuidgen)
    else
        CONVERSATION_ID=$(python3 -c "import uuid; print(str(uuid.uuid4()))")
    fi
    
    # SQLへのエスケープ処理
    ESCAPED_INSTRUCTION=$(echo "$INSTRUCTION" | sed "s/'/''/g")
    ESCAPED_SUBJECT="Beekeeper Instruction"
    
    # SQLite直接挿入
    sqlite3 "$HIVE_DB_PATH" <<EOF
INSERT INTO bee_messages 
(from_bee, to_bee, message_type, subject, content, priority, sender_cli_used, conversation_id, created_at)
VALUES 
('beekeeper', '$TARGET', 'instruction', '$ESCAPED_SUBJECT', '$ESCAPED_INSTRUCTION', '$PRIORITY', 1, '$CONVERSATION_ID', CURRENT_TIMESTAMP);
EOF
    
    if [[ $? -eq 0 ]]; then
        log_info "Fallback SQLite logging successful"
        
        # 自動タスク生成チェック（簡易版）
        if echo "$INSTRUCTION" | grep -qE "(実装|開発|作成|修正|テスト|implement|develop|create|fix|test)"; then
            log_info "Instruction appears to require task creation"
            
            # タスクタイトル抽出（最初の50文字）
            TASK_TITLE="${INSTRUCTION:0:50}"
            if [[ ${#INSTRUCTION} -gt 50 ]]; then
                TASK_TITLE="${TASK_TITLE}..."
            fi
            
            # UUIDベースのタスクID生成
            if command -v uuidgen >/dev/null 2>&1; then
                TASK_ID=$(uuidgen)
            else
                TASK_ID=$(python3 -c "import uuid; print(str(uuid.uuid4()))")
            fi
            
            # エスケープ処理
            ESCAPED_TITLE=$(echo "$TASK_TITLE" | sed "s/'/''/g")
            
            # タスク作成
            sqlite3 "$HIVE_DB_PATH" <<EOF
INSERT INTO tasks 
(task_id, title, description, priority, assigned_to, created_by, metadata)
VALUES 
('$TASK_ID', '$ESCAPED_TITLE', '$ESCAPED_INSTRUCTION', 
 CASE WHEN '$PRIORITY' = 'urgent' THEN 'critical'
      WHEN '$PRIORITY' = 'high' THEN 'high' 
      WHEN '$PRIORITY' = 'normal' THEN 'medium'
      ELSE 'low' END,
 CASE WHEN '$TARGET' = 'all' THEN NULL ELSE '$TARGET' END,
 'beekeeper',
 '{"auto_generated": true, "conversation_id": "$CONVERSATION_ID", "source": "beekeeper_instruction"}'
);
EOF
            
            if [[ $? -eq 0 ]]; then
                log_info "Auto-generated task created (ID: $TASK_ID)"
            else
                log_error "Failed to create auto-generated task"
            fi
        fi
    else
        log_error "Fallback SQLite logging failed"
        exit 1
    fi
fi

# tmuxセッション確認
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    log_info "tmux session '$SESSION_NAME' found"
    
    # sender CLI経由でbeeに指示を送信
    if [[ "$TARGET" == "all" ]]; then
        # 全beeに送信
        for bee in queen developer qa analyst; do
            if tmux list-panes -t "$SESSION_NAME" -F "#{pane_title}" | grep -q "$bee" 2>/dev/null; then
                log_info "Sending instruction to $bee via sender CLI"
                
                # 構造化メッセージ作成
                MESSAGE=$(cat << EOF
## 📨 MESSAGE FROM BEEKEEPER

**Type:** instruction
**Subject:** Beekeeper Instruction
**Task ID:** N/A
**Timestamp:** $(date -Iseconds)

**Content:**
$INSTRUCTION

---
EOF
)
                
                # sender CLI実行
                python3 -m bees.cli send "$SESSION_NAME" "$bee" "$MESSAGE" \
                    --type instruction \
                    --sender beekeeper \
                    --metadata "{\"priority\": \"$PRIORITY\"}" 2>/dev/null
                
                if [[ $? -eq 0 ]]; then
                    log_info "Instruction sent to $bee successfully"
                else
                    log_error "Failed to send instruction to $bee"
                fi
            fi
        done
    else
        # 特定のbeeに送信
        if tmux list-panes -t "$SESSION_NAME" -F "#{pane_title}" | grep -q "$TARGET" 2>/dev/null; then
            log_info "Sending instruction to $TARGET via sender CLI"
            
            MESSAGE=$(cat << EOF
## 📨 MESSAGE FROM BEEKEEPER

**Type:** instruction
**Subject:** Beekeeper Instruction  
**Task ID:** N/A
**Timestamp:** $(date -Iseconds)

**Content:**
$INSTRUCTION

---
EOF
)
            
            python3 -m bees.cli send "$SESSION_NAME" "$TARGET" "$MESSAGE" \
                --type instruction \
                --sender beekeeper \
                --metadata "{\"priority\": \"$PRIORITY\"}" 2>/dev/null
                
            if [[ $? -eq 0 ]]; then
                log_info "Instruction sent to $TARGET successfully"
            else
                log_error "Failed to send instruction to $TARGET"
            fi
        else
            log_error "Target bee '$TARGET' not found in tmux session"
        fi
    fi
else
    log_error "tmux session '$SESSION_NAME' not found"
    log_info "Instruction logged to database but not sent to bees"
fi

log_info "Beekeeper instruction processing completed"