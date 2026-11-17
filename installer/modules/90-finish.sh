# shellcheck shell=bash
# Step "finish": tell the user exactly what happens next.
mod_finish() {
  step "Done"
  cat <<MSG

    Steamed Pi is installed for ${C_B}$TARGET_USER${C_0}.

    What happens next:
      1. Reboot:                  ${C_B}sudo reboot${C_0}
      2. The console boots straight into Steam Big Picture (Gaming Mode).
      3. Sign in to Steam when it asks. This is the only thing you have to do by hand.
      4. Steamed Pi then finishes by itself: it makes Proton (ARM64) the default for Windows games, adds the
         Emulation (ES-DE) entry to your library, and downloads the ARM compatibility tools. Steam restarts once.

    Using it:
      Home button (or Super+Esc)  opens the console menu: resume, Settings, switch to Desktop, power.
      Dashboard                   http://$(hostname).local:8080   (the address and PIN are in the menu under Console info)
      Settings                    Home menu > Settings   (boot mode, screen, startup movie, SSH/FTP, ...)
      Desktop mode                Home menu > Switch to Desktop.  Back: the "Return to Gaming Mode" icon in the dock.
      ROMs                        copy them to ~/ROMs/<system>/ (BIOS files to ~/ROMs/bios/), by FTP from the dashboard or a USB drive

    Games: see docs/COMPATIBILITY.md. Many Windows games do not run on the Pi 5's GPU; tools/compat finds the ones that should.

    Undo everything:  ./uninstall.sh        Log: $LOG_FILE
MSG
  return 0
}
