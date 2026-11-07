import importlib.machinery
import importlib.util
import unittest
from pathlib import Path

_path = str(Path(__file__).resolve().parent.parent / "wifiwalk")
_loader = importlib.machinery.SourceFileLoader("wifiwalk", _path)
_spec = importlib.util.spec_from_loader("wifiwalk", _loader)
ww = importlib.util.module_from_spec(_spec)
_loader.exec_module(ww)

LINK = """Connected to 04:42:1a:00:11:24 (on wlan0)
	SSID: HomeNet
	freq: 5180.0
	RX: 123456 bytes (789 packets)
	TX: 23456 bytes (123 packets)
	signal: -63 dBm
	rx bitrate: 1200.9 MBit/s 80MHz HE-MCS 11 HE-NSS 2 HE-GI 0 HE-DCM 0
	tx bitrate: 960.7 MBit/s 80MHz HE-MCS 9 HE-NSS 2 HE-GI 0 HE-DCM 0

	bss flags: short-slot-time
	dtim period: 3
	beacon int: 100
"""

STATION = """Station 04:42:1a:00:11:24 (on wlan0)
	inactive time:	10 ms
	rx bytes:	123456
	tx packets:	1000
	tx retries:	55
	tx failed:	2
	beacon loss:	1
	signal:  	-63 [-65, -66] dBm
"""

SURVEY = """Survey data from wlan0
	frequency:			5170 MHz
	noise:				-92 dBm
Survey data from wlan0
	frequency:			5180 MHz [in use]
	noise:				-95 dBm
	channel active time:		100 ms
"""

SCAN = """BSS 04:42:1a:00:11:24(on wlan0) -- associated
	last seen: 100 ms ago
	freq: 5180.0
	signal: -63.00 dBm
	SSID: HomeNet
BSS 06:42:1a:00:11:20(on wlan0)
	freq: 2437.0
	signal: -51.00 dBm
	SSID: HomeNet-2.4G
BSS 04:42:1a:00:11:2c(on wlan0)
	freq: 5500.0
	signal: -70.00 dBm
	SSID:
BSS aa:bb:cc:dd:ee:01(on wlan0)
	freq: 5180.0
	signal: -80.00 dBm
	SSID: Neighbour
BSS aa:bb:cc:dd:ee:02(on wlan0)
	freq: 2412.0
	signal: -85.00 dBm
	SSID:
"""

PING = """PING 192.168.1.1 (192.168.1.1) 56(84) bytes of data.
64 bytes from 192.168.1.1: icmp_seq=1 ttl=64 time=2.31 ms
64 bytes from 192.168.1.1: icmp_seq=2 ttl=64 time=4.80 ms
64 bytes from 192.168.1.1: icmp_seq=4 ttl=64 time=30.1 ms

--- 192.168.1.1 ping statistics ---
4 packets transmitted, 3 received, 25% packet loss, time 603ms
"""


class Parse(unittest.TestCase):
    def test_link(self):
        l = ww.parse_link(LINK)
        self.assertEqual(l["bssid"], "04:42:1a:00:11:24")
        self.assertEqual(l["ssid"], "HomeNet")
        self.assertEqual(l["signal"], -63)
        self.assertEqual(l["freq"], 5180.0)
        self.assertEqual(l["tx_rate"], 960.7)
        self.assertEqual(l["width"], 80)
        self.assertIsNone(ww.parse_link("Not connected.\n"))

    def test_station_noise(self):
        self.assertEqual(ww.parse_station(STATION),
                         {"tx_retries": 55, "tx_failed": 2, "beacon_loss": 1, "tx_packets": 1000})
        self.assertEqual(ww.parse_noise(SURVEY), -95)
        self.assertIsNone(ww.parse_noise("Survey data from wlan0\n\tnoise: -90 dBm\n"))

    def test_scan(self):
        aps = ww.parse_scan(SCAN)
        self.assertEqual(len(aps), 5)
        self.assertEqual(aps[1], {"bssid": "06:42:1a:00:11:20", "ssid": "HomeNet-2.4G", "freq": 2437.0, "signal": -51})
        self.assertEqual(aps[4]["ssid"], "")
        self.assertTrue(ww.same_radio_family("c2:ad:9f:7d:61:c1", "6a:ad:9f:7d:61:c5"))
        self.assertFalse(ww.same_radio_family("4c:c4:49:19:ff:bd", "6a:ad:9f:7d:61:c5"))

    def test_ping(self):
        sent, recv, rtts = ww.parse_ping(PING)
        self.assertEqual((sent, recv), (4, 3))
        self.assertEqual(rtts, [2.31, 4.80, 30.1])

    def test_bands_channels(self):
        self.assertEqual((ww.band(2437), ww.channel(2437)), ("2.4", 6))
        self.assertEqual((ww.band(5180), ww.channel(5180)), ("5", 36))
        self.assertEqual((ww.band(5955), ww.channel(5955)), ("6", 1))
        self.assertEqual(ww.verdict(-58), "great")
        self.assertEqual(ww.verdict(-70), "fair")
        self.assertEqual(ww.verdict(-80), "bad")

    def test_summarize(self):
        link = ww.parse_link(LINK)
        samples = [link, dict(link, signal=-70), None, dict(link, signal=-61)]
        r = ww.summarize_spot(samples, ww.parse_ping(PING), ww.parse_scan(SCAN), "HomeNet", -95)
        self.assertEqual(r["signal_median"], -63)
        self.assertEqual(r["signal_min"], -70)
        self.assertEqual(r["snr"], 32)
        self.assertEqual(r["disconnected_samples"], 1)
        self.assertEqual(r["ping_loss_pct"], 25.0)
        self.assertEqual(r["router_bands"]["2.4"]["signal"], -51)
        self.assertEqual(r["router_bands"]["5"]["channel"], 36)
        self.assertEqual(r["same_channel_neighbours"], 1)
        self.assertEqual(r["verdict"], "good")

    def test_clientlist(self):
        data = {"get_clientlist": {
            "maclist": ["AA", "BB", "CC", "DD"],
            "AA": {"name": "Phone", "nickName": "", "isWL": "2", "rssi": "-74", "isOnline": "1",
                   "curTx": "144", "curRx": "86", "ip": "192.168.1.20", "wlConnectTime": "01:02:03"},
            "BB": {"name": "Desktop", "isWL": "0", "rssi": "0", "isOnline": "1"},
            "CC": {"name": "TV", "nickName": "Parents TV", "isWL": "1", "rssi": "-81", "isOnline": "1"},
            "DD": {"name": "Old", "isWL": "1", "rssi": "-60", "isOnline": "0"},
        }}
        cl = ww.parse_clientlist(data)
        self.assertEqual([c["name"] for c in cl], ["Parents TV", "Phone"])
        self.assertEqual(cl[0]["band"], "2.4")
        self.assertEqual(cl[1]["rssi"], -74)


class Report(unittest.TestCase):
    def test_report_runs(self):
        import io, json, tempfile, contextlib
        link = ww.parse_link(LINK)
        rec = ww.summarize_spot([link], ww.parse_ping(PING), ww.parse_scan(SCAN), "HomeNet", -95)
        with tempfile.TemporaryDirectory() as d:
            paths = []
            for name, sig in (("hall", -63), ("living", -58)):
                p = Path(d) / f"{name}.jsonl"
                ww.append(p, {"kind": "survey", "name": name, "time": "2026-01-01T10:00:00"})
                for spot, delta in (("kitchen", 0), ("parents", -15)):
                    ww.append(p, dict(rec, kind="spot", spot=spot, signal_median=sig + delta))
                paths.append(p)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ww.report(paths[:1])
                ww.report(paths)
            out = buf.getvalue()
            self.assertIn("Weakest spot: parents", out)
            self.assertIn("Best placement: living", out)


if __name__ == "__main__":
    unittest.main()
