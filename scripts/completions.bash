# hacker-tool bash completion — v2.3.0
_htctl_complete() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local cmds="deps doctor update backup test edit link clean fix-scan secrets version"
    [[ "${COMP_WORDS[1]}" == "secrets" && $COMP_CWORD -eq 2 ]] && \
        COMPREPLY=($(compgen -W "set get list delete" -- "$cur")) || \
        COMPREPLY=($(compgen -W "$cmds" -- "$cur"))
}
_ht_complete() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    case "${COMP_WORDS[1]}" in
        fs)      COMPREPLY=($(compgen -W "manifest diff integrity disk archive secrets_scan" -- "$cur")) ;;
        net)     COMPREPLY=($(compgen -W "scan dns ssl_audit banner wifi trace mac arpwatch pipeline" -- "$cur")) ;;
        web)     COMPREPLY=($(compgen -W "check headers ssl_check redirects diff fingerprint crawl" -- "$cur")) ;;
        project) COMPREPLY=($(compgen -W "snapshot diff package template timeline" -- "$cur")) ;;
        sync)    COMPREPLY=($(compgen -W "push pull status smb conflicts schedule dryrun" -- "$cur")) ;;
        report) COMPREPLY=($(compgen -W "generate list view csv_export summary diff schedule html" -- "$cur")) ;;
        crypto)  COMPREPLY=($(compgen -W "hash encode keygen encrypt verify" -- "$cur")) ;;
        device)  COMPREPLY=($(compgen -W "battery wifi clipboard notify storage" -- "$cur")) ;;
        vuln)    COMPREPLY=($(compgen -W "cve defaultcreds portrisk ciphers" -- "$cur")) ;;
        proc)    COMPREPLY=($(compgen -W "list kill watch portpid" -- "$cur")) ;;
        *)       COMPREPLY=($(compgen -W "fs net web project sync report crypto device vuln proc" -- "$cur")) ;;
    esac
}
complete -F _htctl_complete htctl
complete -F _ht_complete ht ht-cli hackertool
