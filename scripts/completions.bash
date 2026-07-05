#!/usr/bin/env bash
# scripts/completions.bash — bash tab-completion for htctl and hacker-tool
#
# Activate for the current session:
#   source ~/hacker-tool/scripts/completions.bash
#
# Persist across all sessions — add ONE of these to ~/.bashrc:
#   source ~/hacker-tool/scripts/completions.bash
#   [ -f ~/hacker-tool/scripts/completions.bash ] && \
#       source ~/hacker-tool/scripts/completions.bash
#
# Verified on bash 5.x (Termux/Android). Does not require the external
# bash-completion package — falls back gracefully if unavailable.

# ── internal helpers ────────────────────────────────────────────────────────

__ht_words() {
    if declare -f _init_completion &>/dev/null; then
        _init_completion 2>/dev/null && return 0
    fi
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    words=("${COMP_WORDS[@]}")
    cword=$COMP_CWORD
}

__ht_w() {
    COMPREPLY=($(compgen -W "$1" -- "$cur"))
}

__ht_files() {
    COMPREPLY=($(compgen -f -- "$cur"))
    compopt -o filenames 2>/dev/null
}

__ht_dirs() {
    COMPREPLY=($(compgen -d -- "$cur"))
    compopt -o filenames 2>/dev/null
}

# ── shared flag-value handler ────────────────────────────────────────────────
# Returns 0 (sets COMPREPLY) when prev is a flag expecting a constrained value.
# Returns 1 otherwise so the caller continues normally.

__ht_flag_value() {
    case "$prev" in
        --algo)
            __ht_w "sha256 sha1 md5 sha512 sha224 sha384"
            return 0 ;;
        --fmt)
            __ht_w "md html"
            return 0 ;;
        --sig)
            __ht_w "TERM KILL HUP INT"
            return 0 ;;
        --sort)
            __ht_w "rss_kb cpu_ticks pid"
            return 0 ;;
        --file)
            __ht_files
            return 0 ;;
        --out|--path)
            __ht_dirs
            return 0 ;;
        --root)
            __ht_dirs
            return 0 ;;
        --exclude|--range|--host|--ports|--title|--name| \
        --n|--max|--timeout|--text|--hash-a|--hash-b|--filter)
            return 0 ;;
    esac
    return 1
}

# ── verb+subcommand logic ────────────────────────────────────────────────────
# Shared by both _hacker_tool_complete and _htctl_complete.
# $1=verb  $2=subverb  $3=depth (0=at subverb position, 1+=past it)

__ht_verb() {
    local verb="$1" subverb="$2" depth="$3"

    case "$verb" in

        # ── fs ─────────────────────────────────────────────────────────────
        fs)
            if [[ $depth -eq 0 ]]; then
                __ht_w "manifest diff"
            else
                case "$subverb" in
                    manifest) __ht_w "--root --exclude --no-hash --out" ;;
                    diff)     __ht_files ;;
                esac
            fi ;;

        # ── net ────────────────────────────────────────────────────────────
        net)
            if [[ $depth -eq 0 ]]; then
                __ht_w "scan"
            else
                __ht_w "--range --nmap"
            fi ;;

        # ── web ────────────────────────────────────────────────────────────
        web)
            if [[ $depth -eq 0 ]]; then
                __ht_w "check links"
            else
                case "$subverb" in
                    links) __ht_w "--all-domains" ;;
                esac
            fi ;;

        # ── project ────────────────────────────────────────────────────────
        project)
            if [[ $depth -eq 0 ]]; then
                __ht_w "snapshot"
            else
                __ht_w "--name --out"
            fi ;;

        # ── sync ───────────────────────────────────────────────────────────
        sync)
            if [[ $depth -eq 0 ]]; then
                __ht_w "push pull status"
            fi ;;

        # ── report ─────────────────────────────────────────────────────────
        report)
            __ht_w "--title --fmt --out" ;;

        # ── clean ──────────────────────────────────────────────────────────
        clean)
            __ht_w "--dry-run --path" ;;

        # ── crypto ─────────────────────────────────────────────────────────
        crypto)
            if [[ $depth -eq 0 ]]; then
                __ht_w "hash encode decode entropy compare"
            else
                case "$subverb" in
                    hash)    __ht_w "--file --text --algo" ;;
                    encode)  __ht_w "--file --text --url-safe" ;;
                    decode)  __ht_w "--text --url-safe" ;;
                    entropy) __ht_w "--file" ;;
                    compare) __ht_w "--hash-a --hash-b" ;;
                esac
            fi ;;

        # ── device ─────────────────────────────────────────────────────────
        device)
            if [[ $depth -eq 0 ]]; then
                __ht_w "info storage battery net cpu"
            fi ;;

        # ── vuln ───────────────────────────────────────────────────────────
        vuln)
            if [[ $depth -eq 0 ]]; then
                __ht_w "headers ports perms"
            else
                case "$subverb" in
                    headers) __ht_w "--timeout" ;;
                    ports)   __ht_w "--host --ports --timeout" ;;
                    perms)   __ht_w "--root --max" ;;
                esac
            fi ;;

        # ── proc ───────────────────────────────────────────────────────────
        proc)
            if [[ $depth -eq 0 ]]; then
                __ht_w "list top find kill mem"
            else
                case "$subverb" in
                    list) __ht_w "--filter" ;;
                    top)  __ht_w "--n --sort" ;;
                    kill)
                        if [[ "$cur" == -* ]]; then
                            __ht_w "--sig"
                        else
                            local pids
                            pids=$(ls /proc 2>/dev/null | grep -E '^[0-9]+$' | tr '\n' ' ')
                            __ht_w "$pids"
                        fi ;;
                esac
            fi ;;

    esac
}

# ── hacker-tool.py completion ───────────────────────────────────────────────

_hacker_tool_complete() {
    local cur prev words cword
    __ht_words

    __ht_flag_value && return

    local verb="${words[1]:-}"
    local subverb="${words[2]:-}"
    local depth=$(( cword - 2 ))

    if [[ $cword -eq 1 ]]; then
        __ht_w "fs net web project sync report clean crypto device vuln proc"
        return
    fi

    __ht_verb "$verb" "$subverb" "$depth"
}

# ── htctl completion ────────────────────────────────────────────────────────

_htctl_complete() {
    local cur prev words cword
    __ht_words

    __ht_flag_value && return

    local _HTCTL_NATIVE="deps doctor update upgrade backup test edit \
version run cli link unlink uninstall fix-scan"
    local _HTCTL_PASSTHRU="fs net web project sync report clean \
crypto device vuln proc"

    if [[ $cword -eq 1 ]]; then
        __ht_w "$_HTCTL_NATIVE $_HTCTL_PASSTHRU"
        return
    fi

    local verb="${words[1]:-}"
    local subverb="${words[2]:-}"
    local depth=$(( cword - 2 ))

    # native htctl verbs take no subcommands or flags
    case "$verb" in
        deps|doctor|version|fix-scan|\
        test|edit|run|cli|\
        update|upgrade|backup|uninstall|\
        link|unlink) return ;;
    esac

    # pass-through verbs delegate to shared logic
    __ht_verb "$verb" "$subverb" "$depth"
}

# ── register ────────────────────────────────────────────────────────────────

complete -F _htctl_complete        htctl
complete -F _hacker_tool_complete  hacker-tool
complete -F _hacker_tool_complete  hacker-tool.py
