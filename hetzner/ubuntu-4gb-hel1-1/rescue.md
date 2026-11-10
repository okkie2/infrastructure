# Hetzner Cloud: recover Ubuntu root access from Rescue

This records the recovery performed on 10 November 2026 for the Ubuntu 26.04 VPS in Helsinki. Use it when the installed Ubuntu system rejects the root password and the Hetzner web console is the available way in. The example root partition was `/dev/sda1`; **identify the partition on the current server before mounting anything**.

## Before entering Rescue

The Hetzner web console did not accept `Cmd+V` as a password paste in this session. The password field shows no characters either way, so a failed paste looked like a bad password. **Type the password manually once before starting recovery.** Keep passwords and API tokens out of screenshots and chat.

Hetzner's **Rescue → Reset Root Password** is another documented option. If a manually entered, newly reset Ubuntu password still fails, use the Rescue procedure below. A Rescue password logs into the temporary Rescue system; it does not become Ubuntu's password.

## Finnish keyboard in the Helsinki Rescue console

Hetzner says Rescue uses the keyboard layout of the server's location: a Helsinki server uses Finnish (`fi`). These key positions produced the characters needed for this procedure:

| Character | Finnish layout key position |
| --- | --- |
| `/` | **Shift + 7** |
| `-` | Key immediately to the right of the period (`.`), without Shift |
| `+` | Key immediately to the right of `0`, without Shift |

At an empty shell prompt, type a troublesome character, confirm what appears, then erase it with Backspace **without pressing Enter**. This is especially useful before entering a password, where typed characters are invisible. The installed Ubuntu image has its own keyboard setting; the Finnish Rescue layout does not imply Ubuntu will also use it.

## Recovery steps

1. In Hetzner Console, open the server's **Rescue** tab and select **Enable rescue & power cycle**. Boot into Rescue and log in as `root` with the Rescue password shown by Hetzner (or the SSH key selected during activation). Do not use `Rebuild` or `installimage` for a password recovery; those install an operating system.
2. Identify the installed root partition:

   ```sh
   lsblk -f
   ```

   In this recovery, `/dev/sda1` was the ext4 root partition. `/dev/sda15` was the vfat boot partition. Partition names can differ on another server.
3. Mount the root partition and check that it contains the installed system:

   ```sh
   mount /dev/sda1 /mnt
   ls /mnt
   ```

   Replace `/dev/sda1` if step 2 identified another root partition. There must be a **space** between `/dev/sda1` and `/mnt`. The mistaken `mount /dev/sda1/mnt` produced `can't find in /etc/fstab`. A successful `mount` normally returns silently; `ls /mnt` should show directories such as `etc`, `usr`, and `var`. Stop if the mount fails or those directories are absent.
4. Prepare and enter the installed Ubuntu system, then set its root password:

   ```sh
   chroot-prepare /mnt
   chroot /mnt
   passwd
   ```

   Enter the **new Ubuntu root password** twice. Nothing appears while typing. Choose a long, unique password whose exact characters you can enter under both the Finnish Rescue layout and Ubuntu's layout; 20 or more randomly generated ASCII letters and digits avoid shifted punctuation while remaining strong. Wait for `password updated successfully`. The prompt may still say `root@rescue` after `chroot`; that label alone does not mean `chroot` failed. If a command reports an error, stop there rather than rebooting.

5. After the password change succeeds, leave the chroot and restart:

   ```sh
   exit
   reboot
   ```

   Rescue ends on reboot. Log in at the Ubuntu console as `root` with the new **Ubuntu** password. Enter the same **characters**, accounting for Ubuntu's keyboard layout; repeating the same physical keystrokes can produce a different password. In this recovery, the Ubuntu login succeeded after these steps.

## After access is restored

The web console is an emergency interface. For regular administration, establish and verify SSH access. From the **Ubuntu** console, this read-only command displays the server's public SSH host-key fingerprint so it can be compared with the fingerprint presented to an SSH client:

```sh
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

The fingerprint is safe to share; never share the private key or a password. Changing the root password in the console does not necessarily enable SSH password login.

If the recovery password was temporary or hard to enter, first confirm that key-based SSH works in a **second session**. Then run `passwd` in Ubuntu to replace it with a long, unique password, save that password in a password manager, and verify a fresh Ubuntu console login before closing the working session. A password of 20 or more random letters and digits is easier to type across these layouts than one relying on symbols; symbol rules are not needed for password strength.

## References

- [Hetzner: Resetting the password via Rescue](https://docs.hetzner.com/cloud/servers/how-to-rescue/reset-password/)
- [Hetzner: Using Rescue](https://docs.hetzner.com/cloud/servers/getting-started/rescue-system/)
- [Hetzner Cloud FAQ: console keyboard layout and Helsinki Rescue](https://docs.hetzner.com/cloud/servers/faq/)
- [Finnish keyboard layout mapping (`/`, `-`, `+`)](https://cgit.arctica-project.org/vcxsrv/tree/xorg-server/xkeyboard-config/symbols/fi?h=1.15.2.8&id=b8219a4680768e14b7fe4930adf86e9be261b31f)
- [NIST password guidance: length and no composition rules](https://pages.nist.gov/800-63-4/sp800-63b.html)
