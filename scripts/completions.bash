# hacker-tool bash/zsh completion
# Source from .bashrc:  source ~/hacker-tool/scripts/completions.bash

_htctl_complete() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local cmds="deps doctor update backup test edit link clean fix-scan secrets version"
    local secrets_cmds="set get list delete"

    if [[ "${COMP_WORDS[1]}" == "secrets" && $COMP_CWORD -eq 2 ]]; then
        COMPREPLY=($(compgen -W "$secrets_cmds" -- "$cur"))
    else
        COMPREPLY=($(compgen -W "$cmds" -- "$cur"))
    fi
}

_ht_complete() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local verbs="fs net web project sync report"
    local fs_sub="manifest diff integrity"
    local net_sub="scan arp ping"
    local web_sub="check headers ssl"
    local project_sub="snapshot package"
    local sync_sub="push pull status"
    local report_sub="generate list view"

    case "${COMP_WORDS[1]}" in
        fs)      COMPREPLY=($(compgen -W "$fs_sub"      -- "$cur")) ;;
        net)     COMPREPLY=($(compgen -W "$net_sub"     -- "$cur")) ;;
        web)     COMPREPLY=($(compgen -W "$web_sub"     -- "$cur")) ;;
        project) COMPREPLY=($(compgen -W "$project_sub" -- "$cur")) ;;
        sync)    COMPREPLY=($(compgen -W "$sync_sub"    -- "$cur")) ;;
        report)  COMPREPLY=($(compgen -W "$report_sub"  -- "$cur")) ;;
        *)       COMPREPLY=($(compgen -W "$verbs"       -- "$cur")) ;;
    esac
}

complete -F _htctl_complete htctl
complete -F _ht_complete ht
complete -F _ht_complete ht-cli
complete -F _ht_complete hackertool
