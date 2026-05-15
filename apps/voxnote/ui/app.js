// VoxNote — Vue 3 (CDN, no build) UI mounted into PyWebView.
//
// Talks to Python via `window.pywebview.api.*`. PyWebView resolves promises
// with the bridge return values. We poll for live updates while recording
// rather than maintaining a websocket — simpler and totally fine for a desktop
// app where the producer and consumer share one process.
(function () {
  const { createApp, reactive, ref, computed, onMounted, onUnmounted, watch, nextTick } = Vue;

  // Expose a fake `pywebview.api` when running outside the desktop shell so we
  // can iterate on the UI inside an ordinary browser tab.
  if (!window.pywebview) {
    console.warn("[voxnote] running outside PyWebView; using mock api.");
    const sessions = [];
    let recording = false;
    let recStart = 0;
    const captions = [];
    window.pywebview = {
      api: {
        info:        async () => ({ version: "0.2.0-dev", asr: "echo", llm: "echo" }),
        list_sessions: async () => sessions.slice(),
        get_session: async (id) => sessions.find(s => s.id === id) || null,
        is_recording: async () => recording,
        live_captions: async () => captions.slice(),
        live_summary:  async () => null,
        start_recording: async (title) => {
          recording = true; recStart = Date.now(); captions.length = 0;
          const id = "demo-" + Date.now();
          sessions.unshift({ id, title, started_at: Date.now()/1000, duration_ms: 0 });
          return { ok: true, session_id: id };
        },
        stop_recording: async () => { recording = false; return { ok: true, summary: null }; },
        rename_session: async () => ({ ok: true }),
        delete_session: async () => ({ ok: true }),
        search:         async () => [],
        export:         async (id, fmt) => ({ ok: true, path: "/tmp/demo." + fmt }),
        open_export_dir: async () => ({ ok: true, path: "/tmp" }),
      },
    };
    setInterval(() => {
      if (recording) captions.push({ text: "Lorem ipsum mock caption " + captions.length, final: true, speaker: null, ts: Date.now() - recStart });
    }, 1500);
  }

  const api = window.pywebview.api;

  const App = {
    setup() {
      const info = reactive({});
      const sessions = ref([]);
      const activeSessionId = ref(null);
      const activeTitle = ref("Untitled session");
      const captions = ref([]);
      const summary = ref(null);
      const isRecording = ref(false);
      const recordingMs = ref(0);
      const searchQuery = ref("");
      const searchResults = ref([]);
      const captionPane = ref(null);

      let pollHandle = null;
      let timerHandle = null;
      let recordStart = 0;

      const filteredSessions = computed(() => sessions.value);

      async function refreshInfo() { Object.assign(info, await api.info()); }
      async function refreshSessions() { sessions.value = (await api.list_sessions(200)) || []; }

      async function toggleRecording() {
        if (isRecording.value) {
          const res = await api.stop_recording();
          if (!res.ok) { alert("Could not stop: " + res.error); return; }
          isRecording.value = false;
          stopPolling();
          await refreshSessions();
          if (res.summary) summary.value = res.summary;
        } else {
          const title = activeTitle.value.trim() || "Untitled session";
          const res = await api.start_recording(title);
          if (!res.ok) { alert("Could not start: " + res.error); return; }
          isRecording.value = true;
          activeSessionId.value = res.session_id;
          captions.value = [];
          summary.value = null;
          recordStart = Date.now();
          recordingMs.value = 0;
          startPolling();
          await refreshSessions();
        }
      }

      function startPolling() {
        stopPolling();
        pollHandle = setInterval(async () => {
          if (!isRecording.value) return;
          captions.value = (await api.live_captions()) || [];
          const s = await api.live_summary();
          if (s) summary.value = s;
          await nextTick();
          const pane = captionPane.value;
          if (pane) pane.scrollTop = pane.scrollHeight;
        }, 800);
        timerHandle = setInterval(() => {
          if (isRecording.value) recordingMs.value = Date.now() - recordStart;
        }, 250);
      }

      function stopPolling() {
        if (pollHandle) { clearInterval(pollHandle); pollHandle = null; }
        if (timerHandle) { clearInterval(timerHandle); timerHandle = null; }
      }

      async function openSession(id) {
        if (isRecording.value) return; // don't switch while recording
        const sess = await api.get_session(id);
        if (!sess) return;
        activeSessionId.value = id;
        activeTitle.value = sess.title;
        captions.value = (sess.segments || []).map(seg => ({
          text: seg.text, final: true, speaker: seg.speaker, ts: seg.start_ms,
        }));
        summary.value = sess.summary || null;
      }

      async function saveTitle() {
        if (!activeSessionId.value) return;
        const title = activeTitle.value.trim() || "Untitled session";
        await api.rename_session(activeSessionId.value, title);
        await refreshSessions();
      }

      async function exportSession(fmt) {
        if (!activeSessionId.value) return;
        const res = await api.export(activeSessionId.value, fmt);
        if (res.ok) {
          flash("Exported to " + res.path);
        } else {
          alert("Export failed: " + res.error);
        }
      }

      async function openExportFolder() { await api.open_export_dir(); }

      async function runSearch() {
        const q = searchQuery.value.trim();
        if (!q) { searchResults.value = []; return; }
        searchResults.value = (await api.search(q, 50)) || [];
      }

      // ---- helpers -------------------------------------------------------
      function formatDate(ts) {
        const d = new Date(ts * 1000);
        return d.toLocaleString();
      }
      function formatTs(ms) {
        const s = Math.floor(ms / 1000);
        const h = Math.floor(s / 3600);
        const m = Math.floor((s % 3600) / 60);
        const sec = s % 60;
        return (h > 0 ? String(h).padStart(2, "0") + ":" : "") +
               String(m).padStart(2, "0") + ":" + String(sec).padStart(2, "0");
      }
      function formatDuration(ms) { return formatTs(ms); }

      function flash(msg) {
        // Tiny non-blocking notification — we keep things minimal and write to title.
        const t = document.title;
        document.title = "VoxNote · " + msg;
        setTimeout(() => { document.title = t; }, 2200);
      }

      onMounted(async () => {
        await refreshInfo();
        await refreshSessions();
        const recording = await api.is_recording();
        if (recording) {
          isRecording.value = true;
          recordStart = Date.now();
          startPolling();
        }
      });
      onUnmounted(stopPolling);

      return {
        info, sessions, filteredSessions,
        activeSessionId, activeTitle,
        captions, summary,
        isRecording, recordingMs,
        searchQuery, searchResults,
        captionPane,
        toggleRecording, openSession, saveTitle, exportSession, openExportFolder, runSearch,
        formatDate, formatTs, formatDuration,
      };
    },
  };

  createApp(App).mount("#app");
})();
