import {
  BarChart,
  Button,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Grid,
  H1,
  PieChart,
  Row,
  Select,
  Spacer,
  Stack,
  Stat,
  Table,
  Text,
  TextInput,
  useCanvasAction,
  useCanvasState,
} from "cursor/canvas";

type SessionRecord = {
  id: string;
  status: string;
  resource_count: number;
  duration_sec: number | null;
  day: string;
  created_at: string;
  error: string | null;
};

type DurationStats = {
  count: number;
  mean_sec: number;
  median_sec: number;
  p90_sec: number;
  max_sec: number;
  min_sec: number;
};

const TIMEZONE = "America/New_York";
const FETCHED_AT = "2026-06-08T22:23:32.385751+00:00";
const CATALOG_TOTAL = 9265;
const DATE_MIN = "2026-05-30";
const DATE_MAX = "2026-06-08";
const ALL_SESSIONS: SessionRecord[] = [
  {
    "id": "31a53d45",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 17.0,
    "day": "2026-06-08",
    "created_at": "2026-06-08 17:55",
    "error": null
  },
  {
    "id": "0cd755f6",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 15.8,
    "day": "2026-06-08",
    "created_at": "2026-06-08 10:43",
    "error": null
  },
  {
    "id": "d6ac81ea",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 238.6,
    "day": "2026-06-08",
    "created_at": "2026-06-08 10:21",
    "error": null
  },
  {
    "id": "715265c5",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 17.6,
    "day": "2026-06-07",
    "created_at": "2026-06-07 12:53",
    "error": null
  },
  {
    "id": "29b921b9",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 5.5,
    "day": "2026-06-07",
    "created_at": "2026-06-07 12:52",
    "error": null
  },
  {
    "id": "22886797",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 9.9,
    "day": "2026-06-06",
    "created_at": "2026-06-06 22:40",
    "error": null
  },
  {
    "id": "eb34340a",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 16.8,
    "day": "2026-06-06",
    "created_at": "2026-06-06 22:38",
    "error": null
  },
  {
    "id": "6e49369d",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 10.2,
    "day": "2026-06-06",
    "created_at": "2026-06-06 12:58",
    "error": null
  },
  {
    "id": "bb50b0b7",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 8.9,
    "day": "2026-06-06",
    "created_at": "2026-06-06 12:50",
    "error": null
  },
  {
    "id": "d24ba007",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 62.3,
    "day": "2026-06-06",
    "created_at": "2026-06-06 12:23",
    "error": null
  },
  {
    "id": "4be949af",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 114.1,
    "day": "2026-06-06",
    "created_at": "2026-06-06 12:19",
    "error": null
  },
  {
    "id": "8ad15611",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 19.3,
    "day": "2026-06-06",
    "created_at": "2026-06-06 12:18",
    "error": null
  },
  {
    "id": "19083464",
    "status": "ingesting",
    "resource_count": 2,
    "duration_sec": 10.5,
    "day": "2026-06-06",
    "created_at": "2026-06-06 12:18",
    "error": null
  },
  {
    "id": "9678d4e0",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 11.5,
    "day": "2026-06-06",
    "created_at": "2026-06-06 12:17",
    "error": null
  },
  {
    "id": "85b2a029",
    "status": "analyzing",
    "resource_count": 2,
    "duration_sec": 13.1,
    "day": "2026-06-06",
    "created_at": "2026-06-06 12:15",
    "error": null
  },
  {
    "id": "ed426167",
    "status": "created",
    "resource_count": 1,
    "duration_sec": 0.0,
    "day": "2026-06-06",
    "created_at": "2026-06-06 12:11",
    "error": null
  },
  {
    "id": "5fd69273",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 26.3,
    "day": "2026-06-06",
    "created_at": "2026-06-06 11:44",
    "error": null
  },
  {
    "id": "31478964",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 10.2,
    "day": "2026-06-06",
    "created_at": "2026-06-06 11:43",
    "error": null
  },
  {
    "id": "4e3131b4",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 16.2,
    "day": "2026-06-05",
    "created_at": "2026-06-05 17:46",
    "error": null
  },
  {
    "id": "562c9c3a",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 59.8,
    "day": "2026-06-05",
    "created_at": "2026-06-05 17:43",
    "error": null
  },
  {
    "id": "98d8a443",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 61.4,
    "day": "2026-06-05",
    "created_at": "2026-06-05 14:59",
    "error": null
  },
  {
    "id": "cd6c95f5",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 25.2,
    "day": "2026-06-05",
    "created_at": "2026-06-05 14:34",
    "error": null
  },
  {
    "id": "fa5912c7",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 27.4,
    "day": "2026-06-05",
    "created_at": "2026-06-05 14:28",
    "error": null
  },
  {
    "id": "dd173b15",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 37.5,
    "day": "2026-06-05",
    "created_at": "2026-06-05 14:24",
    "error": null
  },
  {
    "id": "138cd91a",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 55.8,
    "day": "2026-06-05",
    "created_at": "2026-06-05 14:18",
    "error": null
  },
  {
    "id": "370f0b77",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 27.8,
    "day": "2026-06-05",
    "created_at": "2026-06-05 14:16",
    "error": null
  },
  {
    "id": "f505cdb5",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 11.6,
    "day": "2026-06-05",
    "created_at": "2026-06-05 14:15",
    "error": null
  },
  {
    "id": "9faec790",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 246.2,
    "day": "2026-06-05",
    "created_at": "2026-06-05 14:13",
    "error": null
  },
  {
    "id": "c42f6141",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 24.4,
    "day": "2026-06-05",
    "created_at": "2026-06-05 14:12",
    "error": null
  },
  {
    "id": "a4c8c9eb",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 12.2,
    "day": "2026-06-05",
    "created_at": "2026-06-05 14:10",
    "error": null
  },
  {
    "id": "8472e857",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 13.5,
    "day": "2026-06-05",
    "created_at": "2026-06-05 14:09",
    "error": null
  },
  {
    "id": "08c1eb38",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 14.9,
    "day": "2026-06-05",
    "created_at": "2026-06-05 14:09",
    "error": null
  },
  {
    "id": "a4a657f9",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 12.8,
    "day": "2026-06-05",
    "created_at": "2026-06-05 14:09",
    "error": null
  },
  {
    "id": "25736da7",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 11.9,
    "day": "2026-06-05",
    "created_at": "2026-06-05 14:09",
    "error": null
  },
  {
    "id": "4300bd08",
    "status": "failed",
    "resource_count": 1,
    "duration_sec": 3.5,
    "day": "2026-06-05",
    "created_at": "2026-06-05 14:07",
    "error": "World Bank is temporarily unavailable (HTTP 502). Please try again shortly."
  },
  {
    "id": "9124f741",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 20.0,
    "day": "2026-06-05",
    "created_at": "2026-06-05 14:06",
    "error": null
  },
  {
    "id": "21fb10f0",
    "status": "failed",
    "resource_count": 1,
    "duration_sec": 3.6,
    "day": "2026-06-05",
    "created_at": "2026-06-05 14:06",
    "error": "World Bank is temporarily unavailable (HTTP 502). Please try again shortly."
  },
  {
    "id": "5ad96cbe",
    "status": "failed",
    "resource_count": 2,
    "duration_sec": 2.7,
    "day": "2026-06-05",
    "created_at": "2026-06-05 14:05",
    "error": "World Bank is temporarily unavailable (HTTP 502). Please try again shortly."
  },
  {
    "id": "1a2a0936",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 18.0,
    "day": "2026-06-05",
    "created_at": "2026-06-05 14:05",
    "error": null
  },
  {
    "id": "e0b395d6",
    "status": "failed",
    "resource_count": 1,
    "duration_sec": 3.2,
    "day": "2026-06-05",
    "created_at": "2026-06-05 14:05",
    "error": "World Bank is temporarily unavailable (HTTP 502). Please try again shortly."
  },
  {
    "id": "9700aeca",
    "status": "failed",
    "resource_count": 1,
    "duration_sec": 3.5,
    "day": "2026-06-05",
    "created_at": "2026-06-05 14:04",
    "error": "World Bank is temporarily unavailable (HTTP 502). Please try again shortly."
  },
  {
    "id": "41bf7e64",
    "status": "failed",
    "resource_count": 1,
    "duration_sec": 3.5,
    "day": "2026-06-05",
    "created_at": "2026-06-05 14:00",
    "error": "World Bank is temporarily unavailable (HTTP 502). Please try again shortly."
  },
  {
    "id": "958bc9a6",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 12.7,
    "day": "2026-06-05",
    "created_at": "2026-06-05 14:00",
    "error": null
  },
  {
    "id": "c454caa3",
    "status": "failed",
    "resource_count": 1,
    "duration_sec": 3.7,
    "day": "2026-06-05",
    "created_at": "2026-06-05 13:59",
    "error": "World Bank is temporarily unavailable (HTTP 502). Please try again shortly."
  },
  {
    "id": "caa26990",
    "status": "failed",
    "resource_count": 1,
    "duration_sec": 3.5,
    "day": "2026-06-05",
    "created_at": "2026-06-05 13:59",
    "error": "World Bank is temporarily unavailable (HTTP 502). Please try again shortly."
  },
  {
    "id": "986051b6",
    "status": "failed",
    "resource_count": 1,
    "duration_sec": 3.7,
    "day": "2026-06-05",
    "created_at": "2026-06-05 13:59",
    "error": "World Bank is temporarily unavailable (HTTP 502). Please try again shortly."
  },
  {
    "id": "cb140551",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 10.6,
    "day": "2026-06-05",
    "created_at": "2026-06-05 13:58",
    "error": null
  },
  {
    "id": "c2c3a875",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 20.7,
    "day": "2026-06-05",
    "created_at": "2026-06-05 13:58",
    "error": null
  },
  {
    "id": "5a20b2a9",
    "status": "failed",
    "resource_count": 1,
    "duration_sec": 3.5,
    "day": "2026-06-05",
    "created_at": "2026-06-05 13:58",
    "error": "World Bank is temporarily unavailable (HTTP 502). Please try again shortly."
  },
  {
    "id": "b5264fde",
    "status": "failed",
    "resource_count": 1,
    "duration_sec": 3.3,
    "day": "2026-06-05",
    "created_at": "2026-06-05 13:57",
    "error": "World Bank is temporarily unavailable (HTTP 502). Please try again shortly."
  },
  {
    "id": "c38f106e",
    "status": "failed",
    "resource_count": 1,
    "duration_sec": 3.2,
    "day": "2026-06-05",
    "created_at": "2026-06-05 13:57",
    "error": "World Bank is temporarily unavailable (HTTP 502). Please try again shortly."
  },
  {
    "id": "cf3a58eb",
    "status": "failed",
    "resource_count": 2,
    "duration_sec": 3.3,
    "day": "2026-06-05",
    "created_at": "2026-06-05 13:57",
    "error": "World Bank is temporarily unavailable (HTTP 502). Please try again shortly."
  },
  {
    "id": "676cfc20",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 13.6,
    "day": "2026-06-05",
    "created_at": "2026-06-05 13:56",
    "error": null
  },
  {
    "id": "bf969a96",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 10.6,
    "day": "2026-06-05",
    "created_at": "2026-06-05 13:54",
    "error": null
  },
  {
    "id": "2a162d45",
    "status": "failed",
    "resource_count": 1,
    "duration_sec": 3.4,
    "day": "2026-06-05",
    "created_at": "2026-06-05 13:53",
    "error": "World Bank is temporarily unavailable (HTTP 502). Please try again shortly."
  },
  {
    "id": "009edee4",
    "status": "failed",
    "resource_count": 2,
    "duration_sec": 243.4,
    "day": "2026-06-05",
    "created_at": "2026-06-05 13:49",
    "error": "World Bank is temporarily unavailable (HTTP 502). Please try again shortly."
  },
  {
    "id": "779ddf99",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 35.9,
    "day": "2026-06-05",
    "created_at": "2026-06-05 13:45",
    "error": null
  },
  {
    "id": "3eb55144",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 45.1,
    "day": "2026-06-05",
    "created_at": "2026-06-05 13:37",
    "error": null
  },
  {
    "id": "269e3f29",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 65.6,
    "day": "2026-06-05",
    "created_at": "2026-06-05 13:35",
    "error": null
  },
  {
    "id": "16243736",
    "status": "failed",
    "resource_count": 1,
    "duration_sec": 10.5,
    "day": "2026-06-05",
    "created_at": "2026-06-05 13:26",
    "error": "Invalid Input Error: JSON transform error in file \"/tmp/tmpzej1vsjy.json\", in record/value 30758: Object {\"created\":\"201"
  },
  {
    "id": "d6dea1ee",
    "status": "failed",
    "resource_count": 2,
    "duration_sec": 7.9,
    "day": "2026-06-05",
    "created_at": "2026-06-05 13:21",
    "error": "Invalid Input Error: JSON transform error in file \"/tmp/tmpdzqpuqap.json\", in record/value 30758: Object {\"created\":\"201"
  },
  {
    "id": "86fefb62",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 29.8,
    "day": "2026-06-05",
    "created_at": "2026-06-05 12:59",
    "error": null
  },
  {
    "id": "19e509b2",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 165.9,
    "day": "2026-06-05",
    "created_at": "2026-06-05 10:17",
    "error": null
  },
  {
    "id": "8009fee5",
    "status": "failed",
    "resource_count": 2,
    "duration_sec": 6465.1,
    "day": "2026-06-05",
    "created_at": "2026-06-05 10:10",
    "error": "Analysis took longer than expected and was stopped. Go back to search and try again."
  },
  {
    "id": "c4311075",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 40.1,
    "day": "2026-06-01",
    "created_at": "2026-06-01 16:00",
    "error": null
  },
  {
    "id": "a9c4777d",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 53.0,
    "day": "2026-06-01",
    "created_at": "2026-06-01 15:59",
    "error": null
  },
  {
    "id": "30e87ba6",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 333.6,
    "day": "2026-06-01",
    "created_at": "2026-06-01 00:01",
    "error": null
  },
  {
    "id": "a3d73be9",
    "status": "failed",
    "resource_count": 2,
    "duration_sec": 382069.9,
    "day": "2026-05-31",
    "created_at": "2026-05-31 23:59",
    "error": "Analysis took longer than expected and was stopped. Go back to search and try again."
  },
  {
    "id": "cc0728dc",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 50.4,
    "day": "2026-05-31",
    "created_at": "2026-05-31 23:57",
    "error": null
  },
  {
    "id": "6fa36b26",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 370.0,
    "day": "2026-05-31",
    "created_at": "2026-05-31 23:52",
    "error": null
  },
  {
    "id": "5204d97b",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 12.1,
    "day": "2026-05-31",
    "created_at": "2026-05-31 21:29",
    "error": null
  },
  {
    "id": "5e5fc483",
    "status": "failed",
    "resource_count": 2,
    "duration_sec": 364.9,
    "day": "2026-05-31",
    "created_at": "2026-05-31 21:08",
    "error": "World Bank is temporarily unavailable (network error after 3 attempts). Please try again shortly."
  },
  {
    "id": "9525133e",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 261.1,
    "day": "2026-05-31",
    "created_at": "2026-05-31 21:02",
    "error": null
  },
  {
    "id": "38164449",
    "status": "failed",
    "resource_count": 1,
    "duration_sec": 1603.1,
    "day": "2026-05-31",
    "created_at": "2026-05-31 21:01",
    "error": "Load was interrupted or timed out (often happens if the API restarted). Go back to search and try again."
  },
  {
    "id": "de0c3dff",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 99.4,
    "day": "2026-05-31",
    "created_at": "2026-05-31 20:36",
    "error": null
  },
  {
    "id": "1aaef0dc",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 458.5,
    "day": "2026-05-31",
    "created_at": "2026-05-31 20:27",
    "error": null
  },
  {
    "id": "60001b04",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 103.5,
    "day": "2026-05-31",
    "created_at": "2026-05-31 20:24",
    "error": null
  },
  {
    "id": "05f327bc",
    "status": "failed",
    "resource_count": 1,
    "duration_sec": 2376.7,
    "day": "2026-05-31",
    "created_at": "2026-05-31 20:22",
    "error": "Load was interrupted or timed out (often happens if the API restarted). Go back to search and try again."
  },
  {
    "id": "e5e95c6e",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 16.4,
    "day": "2026-05-31",
    "created_at": "2026-05-31 20:20",
    "error": null
  },
  {
    "id": "57a13559",
    "status": "failed",
    "resource_count": 2,
    "duration_sec": 2563.3,
    "day": "2026-05-31",
    "created_at": "2026-05-31 20:19",
    "error": "Load was interrupted or timed out (often happens if the API restarted). Go back to search and try again."
  },
  {
    "id": "d324233b",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 43.5,
    "day": "2026-05-31",
    "created_at": "2026-05-31 20:17",
    "error": null
  },
  {
    "id": "6f1007a4",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 146.1,
    "day": "2026-05-31",
    "created_at": "2026-05-31 20:15",
    "error": null
  },
  {
    "id": "0d6f5b3c",
    "status": "failed",
    "resource_count": 1,
    "duration_sec": 2880.6,
    "day": "2026-05-31",
    "created_at": "2026-05-31 20:13",
    "error": "Load was interrupted or timed out (often happens if the API restarted). Go back to search and try again."
  },
  {
    "id": "14c5d822",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 96.8,
    "day": "2026-05-31",
    "created_at": "2026-05-31 18:59",
    "error": null
  },
  {
    "id": "70c412ba",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 72.0,
    "day": "2026-05-31",
    "created_at": "2026-05-31 18:36",
    "error": null
  },
  {
    "id": "1cb244e5",
    "status": "failed",
    "resource_count": 1,
    "duration_sec": 6276.1,
    "day": "2026-05-31",
    "created_at": "2026-05-31 18:29",
    "error": "Load was interrupted or timed out (often happens if the API restarted). Go back to search and try again."
  },
  {
    "id": "267cd0a7",
    "status": "failed",
    "resource_count": 1,
    "duration_sec": 342.6,
    "day": "2026-05-31",
    "created_at": "2026-05-31 18:22",
    "error": "Load was interrupted or timed out (often happens if the API restarted). Go back to search and try again."
  },
  {
    "id": "bc29b8f4",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 13.5,
    "day": "2026-05-31",
    "created_at": "2026-05-31 18:21",
    "error": null
  },
  {
    "id": "49f485ee",
    "status": "failed",
    "resource_count": 1,
    "duration_sec": 388.0,
    "day": "2026-05-31",
    "created_at": "2026-05-31 18:16",
    "error": "Load was interrupted or timed out (often happens if the API restarted). Go back to search and try again."
  },
  {
    "id": "be92c478",
    "status": "failed",
    "resource_count": 1,
    "duration_sec": 435.7,
    "day": "2026-05-31",
    "created_at": "2026-05-31 18:15",
    "error": "Load was interrupted or timed out (often happens if the API restarted). Go back to search and try again."
  },
  {
    "id": "a10df77f",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 61.8,
    "day": "2026-05-30",
    "created_at": "2026-05-30 23:54",
    "error": null
  },
  {
    "id": "55e92a6b",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 15.4,
    "day": "2026-05-30",
    "created_at": "2026-05-30 23:51",
    "error": null
  },
  {
    "id": "08bdd45d",
    "status": "failed",
    "resource_count": 2,
    "duration_sec": 323.2,
    "day": "2026-05-30",
    "created_at": "2026-05-30 23:41",
    "error": "Load was interrupted or timed out (often happens if the API restarted). Go back to search and try again."
  },
  {
    "id": "acae749d",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 5.9,
    "day": "2026-05-30",
    "created_at": "2026-05-30 23:40",
    "error": null
  },
  {
    "id": "1f58e5ab",
    "status": "failed",
    "resource_count": 2,
    "duration_sec": 484.0,
    "day": "2026-05-30",
    "created_at": "2026-05-30 23:38",
    "error": "Load was interrupted or timed out (often happens if the API restarted). Go back to search and try again."
  },
  {
    "id": "f10f04dc",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 58.7,
    "day": "2026-05-30",
    "created_at": "2026-05-30 23:33",
    "error": null
  },
  {
    "id": "6cb250b6",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 24.1,
    "day": "2026-05-30",
    "created_at": "2026-05-30 23:30",
    "error": null
  },
  {
    "id": "529c5fb8",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 248.4,
    "day": "2026-05-30",
    "created_at": "2026-05-30 23:29",
    "error": null
  },
  {
    "id": "508c975d",
    "status": "complete",
    "resource_count": 2,
    "duration_sec": 19.0,
    "day": "2026-05-30",
    "created_at": "2026-05-30 22:35",
    "error": null
  },
  {
    "id": "ee9ba163",
    "status": "complete",
    "resource_count": 1,
    "duration_sec": 16.2,
    "day": "2026-05-30",
    "created_at": "2026-05-30 21:46",
    "error": null
  }
];
const API_USAGE = [
  {
    "month": "2026-06",
    "tokens_in": 715527,
    "tokens_out": 25632,
    "cost_usd": 2.161531,
    "calls": 77
  },
  {
    "month": "2026-05",
    "tokens_in": 53651,
    "tokens_out": 3206,
    "cost_usd": 0.178535,
    "calls": 15
  }
];
const VISITORS = {
  "tracking_since": null,
  "total_page_views": 0,
  "unique_visitors_all_time": 0,
  "window_days": 30,
  "page_views_in_window": 0,
  "unique_visitors_in_window": 0,
  "unique_visitors_with_analysis": 0,
  "daily_unique_visitors": [],
  "top_paths": [],
  "note": "Deploy web+API update to start visitor tracking."
};

const LIMITATIONS = {
  users: "Unique visitors use an anonymous browser UUID (localStorage), not accounts.",
  time_on_app: "Time on site is approximated by page views — not dwell time per page.",
  window_note: "Based on last 100 analysis runs. Use the date filter below.",
};

function formatSec(sec: number | null | undefined): string {
  if (sec == null) return "—";
  if (sec < 60) return `${Math.round(sec)}s`;
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

function formatEt(iso: string, withDate = true): string {
  const d = new Date(iso);
  if (withDate) {
    return `${d.toLocaleString("en-US", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: TIMEZONE,
    })} ET`;
  }
  return `${d.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    timeZone: TIMEZONE,
  })} ET`;
}

function shortReason(reason: string): string {
  if (reason.startsWith("World Bank")) return "World Bank unavailable";
  if (reason.startsWith("Load was interrupted")) return "Load interrupted / timeout";
  if (reason.startsWith("Analysis took longer")) return "Analysis stale timeout";
  if (reason.startsWith("Invalid Input")) return "JSON ingest error";
  return reason.length > 42 ? `${reason.slice(0, 42)}…` : reason;
}

function statusTone(
  status: string,
): "success" | "danger" | "warning" | "info" | "neutral" {
  if (status === "complete") return "success";
  if (status === "failed") return "danger";
  if (status === "ingesting" || status === "analyzing") return "info";
  return "neutral";
}

function percentile(sorted: number[], p: number): number {
  if (sorted.length === 0) return 0;
  if (sorted.length === 1) return sorted[0];
  const k = (sorted.length - 1) * (p / 100);
  const f = Math.floor(k);
  const c = Math.min(f + 1, sorted.length - 1);
  if (f === c) return sorted[f];
  return sorted[f] + (sorted[c] - sorted[f]) * (k - f);
}

function durationStats(durations: number[]): DurationStats | null {
  if (durations.length === 0) return null;
  const s = [...durations].sort((a, b) => a - b);
  const sum = s.reduce((a, b) => a + b, 0);
  const mid = Math.floor(s.length / 2);
  const median = s.length % 2 === 0 ? (s[mid - 1] + s[mid]) / 2 : s[mid];
  return {
    count: s.length,
    mean_sec: Math.round((sum / s.length) * 10) / 10,
    median_sec: Math.round(median * 10) / 10,
    p90_sec: Math.round(percentile(s, 90) * 10) / 10,
    max_sec: Math.round(s[s.length - 1] * 10) / 10,
    min_sec: Math.round(s[0] * 10) / 10,
  };
}

function addDays(isoDay: string, delta: number): string {
  const [y, m, d] = isoDay.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  dt.setUTCDate(dt.getUTCDate() + delta);
  return dt.toISOString().slice(0, 10);
}

function resolveRange(
  preset: string,
  from: string,
  to: string,
): { from: string; to: string; label: string } {
  if (preset === "7d") {
    const start = addDays(DATE_MAX, -6);
    return { from: start < DATE_MIN ? DATE_MIN : start, to: DATE_MAX, label: "Last 7 days" };
  }
  if (preset === "30d") {
    const start = addDays(DATE_MAX, -29);
    return { from: start < DATE_MIN ? DATE_MIN : start, to: DATE_MAX, label: "Last 30 days" };
  }
  if (preset === "custom" && from && to) {
    return { from: from < to ? from : to, to: from < to ? to : from, label: `${from} → ${to}` };
  }
  return { from: DATE_MIN, to: DATE_MAX, label: "All loaded runs" };
}

function filterSessions(sessions: SessionRecord[], from: string, to: string): SessionRecord[] {
  return sessions.filter((s) => s.day && s.day >= from && s.day <= to);
}

function aggregate(sessions: SessionRecord[]) {
  const byStatus: Record<string, number> = {};
  const failures: Record<string, number> = {};
  const daily: Record<string, number> = {};
  const completeDurations: number[] = [];
  const allDurations: number[] = [];
  let twoDataset = 0;

  for (const s of sessions) {
    byStatus[s.status] = (byStatus[s.status] ?? 0) + 1;
    if (s.day) daily[s.day] = (daily[s.day] ?? 0) + 1;
    if (s.duration_sec != null) {
      allDurations.push(s.duration_sec);
      if (s.status === "complete") completeDurations.push(s.duration_sec);
    }
    if (s.status === "failed" && s.error) {
      failures[s.error] = (failures[s.error] ?? 0) + 1;
    }
    if (s.resource_count >= 2) twoDataset += 1;
  }

  const failureReasons = Object.entries(failures)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([reason, count]) => ({ reason, count }));

  const dailyRuns = Object.entries(daily)
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([day, runs]) => ({ day, runs }));

  return {
    count: sessions.length,
    byStatus,
    twoDataset,
    durationComplete: durationStats(completeDurations),
    durationAll: durationStats(allDurations),
    dailyRuns,
    failureReasons,
    tableSessions: sessions.slice(0, 25),
  };
}

export default function FindingsOpsDashboard() {
  const dispatch = useCanvasAction();
  const [preset, setPreset] = useCanvasState("datePreset", "all");
  const [dateFrom, setDateFrom] = useCanvasState("dateFrom", DATE_MIN);
  const [dateTo, setDateTo] = useCanvasState("dateTo", DATE_MAX);

  const range = resolveRange(preset, dateFrom, dateTo);
  const filtered = filterSessions(ALL_SESSIONS, range.from, range.to);
  const agg = aggregate(filtered);

  const complete = agg.byStatus.complete ?? 0;
  const failed = agg.byStatus.failed ?? 0;
  const sampled = agg.count;
  const successRate = sampled > 0 ? Math.round((complete / sampled) * 100) : 0;
  const currentAi = API_USAGE[0];
  const dur = agg.durationComplete;

  const statusPie = Object.entries(agg.byStatus).map(([label, value]) => ({
    label,
    value,
    tone: statusTone(label),
  }));

  const failureChart = agg.failureReasons.slice(0, 5).map((f) => ({
    label: shortReason(f.reason),
    value: f.count,
  }));

  return (
    <Stack gap={20}>
      <Row align="center" wrap>
        <Stack gap={4}>
          <H1>Findings ops dashboard</H1>
          <Text tone="secondary" size="small">
            Source: production API · fetched {formatEt(FETCHED_AT)} (Eastern)
          </Text>
        </Stack>
        <Spacer />
        <Button
          variant="primary"
          onClick={() =>
            dispatch({
              type: "newComposerChat",
              userPrompt:
                "Refresh the Findings ops dashboard canvas with latest production metrics.",
            })
          }
        >
          Refresh in chat
        </Button>
      </Row>

      <Card>
        <CardHeader label="Date filter (Eastern)" />
        <CardBody>
          <Row gap={12} align="end" wrap>
            <Stack gap={4} style={{ minWidth: 180 }}>
              <Text size="small" tone="secondary">
                Range
              </Text>
              <Select
                value={preset}
                onChange={setPreset}
                options={[
                  { value: "all", label: "All loaded runs" },
                  { value: "7d", label: "Last 7 days" },
                  { value: "30d", label: "Last 30 days" },
                  { value: "custom", label: "Custom range" },
                ]}
              />
            </Stack>
            {preset === "custom" ? (
              <>
                <Stack gap={4} style={{ minWidth: 140 }}>
                  <Text size="small" tone="secondary">
                    From (ET date)
                  </Text>
                  <TextInput
                    value={dateFrom}
                    onChange={setDateFrom}
                    placeholder="YYYY-MM-DD"
                  />
                </Stack>
                <Stack gap={4} style={{ minWidth: 140 }}>
                  <Text size="small" tone="secondary">
                    To (ET date)
                  </Text>
                  <TextInput
                    value={dateTo}
                    onChange={setDateTo}
                    placeholder="YYYY-MM-DD"
                  />
                </Stack>
              </>
            ) : null}
            <Stack gap={4}>
              <Text size="small" tone="secondary">
                Showing
              </Text>
              <Text weight="semibold">
                {range.label} · {sampled} run{sampled === 1 ? "" : "s"}
              </Text>
              <Text size="small" tone="tertiary">
                Data spans {DATE_MIN} to {DATE_MAX} (Eastern dates)
              </Text>
            </Stack>
          </Row>
        </CardBody>
      </Card>

      <Callout tone="info">
        <Stack gap={6}>
          <Text weight="semibold">What this measures</Text>
          <Text size="small">{LIMITATIONS.users}</Text>
          <Text size="small">{LIMITATIONS.time_on_app}</Text>
          <Text size="small" tone="secondary">
            {LIMITATIONS.window_note} Times and dates use US Eastern (ET). AI usage table is monthly.
          </Text>
          <Text size="small" tone="secondary">{VISITORS.note}</Text>
        </Stack>
      </Callout>

      {VISITORS.total_page_views > 0 ? (
        <Card>
          <CardHeader label="Unique visitors (anonymous)" />
          <CardBody>
            <Grid columns={4} gap={12}>
              <Stat
                label="Unique visitors (30d)"
                value={String(VISITORS.unique_visitors_in_window)}
                tone="info"
              />
              <Stat
                label="Page views (30d)"
                value={String(VISITORS.page_views_in_window)}
                tone="neutral"
              />
              <Stat
                label="Visitors who ran analysis"
                value={String(VISITORS.unique_visitors_with_analysis)}
                tone="success"
              />
              <Stat
                label="Unique visitors (all time)"
                value={String(VISITORS.unique_visitors_all_time)}
                tone="neutral"
              />
            </Grid>
            {VISITORS.daily_unique_visitors.length > 0 ? (
              <Stack gap={8} style={{ marginTop: 16 }}>
                <Text size="small" weight="semibold">Daily unique visitors (ET)</Text>
                <BarChart
                  categories={VISITORS.daily_unique_visitors.map((d) => String(d.day).slice(5))}
                  series={[{
                    name: "Unique visitors",
                    data: VISITORS.daily_unique_visitors.map((d) => d.visitors),
                    tone: "info",
                  }]}
                  height={180}
                />
              </Stack>
            ) : null}
            {VISITORS.top_paths.length > 0 ? (
              <Stack gap={8} style={{ marginTop: 16 }}>
                <Text size="small" weight="semibold">Top pages (30d)</Text>
                <Table
                  headers={["Path", "Views", "Unique visitors"]}
                  rows={VISITORS.top_paths.map((p) => [
                    p.path,
                    String(p.views),
                    String(p.visitors),
                  ])}
                />
              </Stack>
            ) : null}
          </CardBody>
        </Card>
      ) : null}

      {sampled === 0 ? (
        <Callout tone="warning" title="No runs in this date range">
          <Text size="small">Adjust the filter — loaded data only covers {DATE_MIN} through {DATE_MAX} (ET).</Text>
        </Callout>
      ) : (
        <>
          <Grid columns={4} gap={12}>
            <Stat label="Analysis runs" value={String(sampled)} tone="info" />
            <Stat label="Completed" value={`${complete} (${successRate}%)`} tone="success" />
            <Stat label="Failed" value={String(failed)} tone="danger" />
            <Stat label="Catalog resources" value={String(CATALOG_TOTAL)} tone="neutral" />
          </Grid>

          <Grid columns={4} gap={12}>
            <Stat
              label="Median analysis time (complete)"
              value={formatSec(dur?.median_sec)}
              tone="info"
            />
            <Stat label="P90 analysis time" value={formatSec(dur?.p90_sec)} tone="info" />
            <Stat
              label="Two-dataset runs"
              value={`${agg.twoDataset} (${sampled > 0 ? Math.round((agg.twoDataset / sampled) * 100) : 0}%)`}
              tone="neutral"
            />
            <Stat
              label="AI spend (current month)"
              value={`$${currentAi.cost_usd.toFixed(2)} · ${currentAi.calls} calls`}
              tone="warning"
            />
          </Grid>

          {agg.dailyRuns.length > 0 ? (
            <Grid columns={2} gap={16}>
              <Card>
                <CardHeader label="Analysis runs per day (ET)" />
                <CardBody>
                  <BarChart
                    categories={agg.dailyRuns.map((d) => d.day.slice(5))}
                    series={[{ name: "Runs", data: agg.dailyRuns.map((d) => d.runs), tone: "info" }]}
                    height={200}
                  />
                  <Text size="small" tone="secondary" style={{ marginTop: 8 }}>
                    Eastern dates · {range.from} to {range.to}
                  </Text>
                </CardBody>
              </Card>

              {statusPie.length > 0 ? (
                <Card>
                  <CardHeader label="Run status mix" />
                  <CardBody>
                    <Row align="center" gap={24}>
                      <PieChart data={statusPie} size={160} donut />
                      <Stack gap={6}>
                        {statusPie.map((s) => (
                          <Text key={s.label} size="small">
                            {s.label}: {s.value}
                          </Text>
                        ))}
                      </Stack>
                    </Row>
                    <Text size="small" tone="secondary" style={{ marginTop: 8 }}>
                      Source: {sampled} sessions in selected range
                    </Text>
                  </CardBody>
                </Card>
              ) : null}
            </Grid>
          ) : null}

          {dur ? (
            <Card>
              <CardHeader label="Completed analysis duration" />
              <CardBody>
                <Grid columns={5} gap={12}>
                  <Stat label="Runs" value={String(dur.count)} tone="neutral" />
                  <Stat label="Median" value={formatSec(dur.median_sec)} tone="info" />
                  <Stat label="Mean" value={formatSec(dur.mean_sec)} tone="info" />
                  <Stat label="P90" value={formatSec(dur.p90_sec)} tone="info" />
                  <Stat label="Max" value={formatSec(dur.max_sec)} tone="warning" />
                </Grid>
                {agg.durationAll ? (
                  <Text size="small" tone="secondary" style={{ marginTop: 12 }}>
                    All statuses mean: {formatSec(agg.durationAll.mean_sec)} (includes failed/stuck runs).
                  </Text>
                ) : null}
              </CardBody>
            </Card>
          ) : null}

          <Grid columns={2} gap={16}>
            {failureChart.length > 0 ? (
              <Card>
                <CardHeader label="Top failure reasons" />
                <CardBody>
                  <BarChart
                    categories={failureChart.map((f) => f.label)}
                    series={[
                      { name: "Failures", data: failureChart.map((f) => f.value), tone: "danger" },
                    ]}
                    horizontal
                    height={220}
                  />
                  <Text size="small" tone="secondary" style={{ marginTop: 8 }}>
                    Source: failed runs in selected range
                  </Text>
                </CardBody>
              </Card>
            ) : null}

            <Card>
              <CardHeader label="Anthropic API usage" />
              <CardBody>
                <Table
                  headers={["Month", "Calls", "Tokens in", "Tokens out", "Est. cost"]}
                  rows={API_USAGE.map((u) => [
                    u.month,
                    String(u.calls),
                    u.tokens_in.toLocaleString(),
                    u.tokens_out.toLocaleString(),
                    `$${u.cost_usd.toFixed(2)}`,
                  ])}
                />
                <Text size="small" tone="secondary" style={{ marginTop: 8 }}>
                  Monthly ledger — not filtered by date range above
                </Text>
              </CardBody>
            </Card>
          </Grid>

          <Card>
            <CardHeader label="Analysis runs in range" />
            <CardBody>
              <Table
                headers={["When (ET)", "Session", "Status", "Datasets", "Duration", "Error"]}
                rows={agg.tableSessions.map((s) => [
                  s.created_at,
                  s.id,
                  s.status,
                  String(s.resource_count),
                  formatSec(s.duration_sec),
                  s.error ? shortReason(s.error) : "—",
                ])}
                rowTone={agg.tableSessions.map((s) => statusTone(s.status))}
              />
              {sampled > 25 ? (
                <Text size="small" tone="secondary" style={{ marginTop: 8 }}>
                  Showing 25 of {sampled} runs
                </Text>
              ) : null}
            </CardBody>
          </Card>
        </>
      )}

      <Text size="small" tone="tertiary">
        Filter state is saved with the canvas. Ask in chat to refresh underlying data.
      </Text>
    </Stack>
  );
}
