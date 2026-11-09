// pcsx2key: помощник драйвера PCSX2 (macOS).
//   pcsx2key win <pid>                 -> "<windowNumber> <w> <h>" главного окна процесса
//   pcsx2key key <pid> <keycode> <down|up>
//   pcsx2key tap <pid> <keycode> <ms>  -> нажать, подержать, отпустить
import Cocoa
import ApplicationServices
let a = CommandLine.arguments
func post(_ pid: pid_t, _ code: CGKeyCode, _ down: Bool) {
    let e = CGEvent(keyboardEventSource: nil, virtualKey: code, keyDown: down)!
    e.postToPid(pid)
}
guard a.count >= 3 else { print("usage"); exit(2) }
let pid = pid_t(a[2])!
switch a[1] {
case "win":
    let list = CGWindowListCopyWindowInfo([.optionOnScreenOnly], kCGNullWindowID) as? [[String: Any]] ?? []
    var best: (Int, Int, Int, Int)? = nil
    for w in list where (w[kCGWindowOwnerPID as String] as? Int32) == pid && (w[kCGWindowLayer as String] as? Int) == 0 {
        let b = w[kCGWindowBounds as String] as? [String: Any] ?? [:]
        let width = (b["Width"] as? Int) ?? 0, height = (b["Height"] as? Int) ?? 0
        if width * height > (best?.1 ?? 0) * (best?.2 ?? 0) { best = ((w[kCGWindowNumber as String] as? Int) ?? 0, width, height, 0) }
    }
    if let b = best { print(b.0, b.1, b.2) } else { print("none"); exit(1) }
case "key":
    post(pid, CGKeyCode(a[3])!, a[4] == "down")
case "tap":
    let c = CGKeyCode(a[3])!
    post(pid, c, true); usleep(useconds_t(Int(a[4])! * 1000)); post(pid, c, false)
default: print("usage"); exit(2)
}
