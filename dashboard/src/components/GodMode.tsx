
import React, { useEffect, useState, useRef } from 'react';

interface AgentState {
    status: string;
    screenshot?: string;
    thoughts?: string;
    step?: number;
    task?: string;
    mode?: string;
}

interface SwarmResult {
    agent: string;
    result: string;
}

interface MemoryStats {
    total_memories: number;
    total_accumulated_experience: number;
}

export const GodMode: React.FC = () => {
    const [state, setState] = useState<AgentState>({ status: 'idle' });
    const [logs, setLogs] = useState<string[]>([]);
    const [inputTask, setInputTask] = useState('');
    const [swarmResults, setSwarmResults] = useState<SwarmResult[]>([]);
    const [memoryStats, setMemoryStats] = useState<MemoryStats>({ total_memories: 0, total_accumulated_experience: 0 });
    const wsRef = useRef<WebSocket | null>(null);
    const logContainerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        // Connect to WebSocket
        wsRef.current = new WebSocket('ws://localhost:8000/ws');

        wsRef.current.onopen = () => {
            console.log('Connected to God Mode Server');
            addLog('System: Connected to Neural Interface');
        };

        wsRef.current.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleMessage(data);
        };

        wsRef.current.onclose = () => {
            addLog('System: Disconnected');
        };

        // Poll memory stats
        const interval = setInterval(fetchMemoryStats, 5000);
        fetchMemoryStats();

        return () => {
            wsRef.current?.close();
            clearInterval(interval);
        };
    }, []);

    useEffect(() => {
        if (logContainerRef.current) {
            logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
        }
    }, [logs]);

    const fetchMemoryStats = async () => {
        try {
            const res = await fetch('http://localhost:8000/memory/stats');
            const data = await res.json();
            setMemoryStats(data);
        } catch (e) {
            // ignore errors
        }
    };

    const handleMessage = (data: any) => {
        if (data.type === 'update') {
            setState(prev => ({
                ...prev,
                screenshot: data.screenshot || prev.screenshot,
                thoughts: data.thoughts,
                step: data.step,
                status: data.status
            }));
            if (data.thoughts) addLog(`Agent: ${data.thoughts}`);
        } else if (data.type === 'status') {
            setState(prev => ({ ...prev, status: data.status, task: data.task || prev.task, mode: data.mode }));
            addLog(`System: Status changed to ${data.status} [Mode: ${data.mode || 'Standard'}]`);
            if (data.status === 'swarm_started') {
                setSwarmResults([]); // Clear previous results
            }
        } else if (data.type === 'error') {
            addLog(`Error: ${data.error}`);
        } else if (data.type === 'swarm_step') {
            // Incremental update from a sub-agent
            addLog(`Swarm [${data.agent}]: Task completed.`);
            setSwarmResults(prev => [...prev, { agent: data.agent, result: data.result }]);
        } else if (data.type === 'swarm_result') {
            addLog(`System: CEO Agent received all reports.`);
            // If we receive the full bulk result at once (e.g. real mode sometimes), merge it
            if (data.result.results) {
                const newResults = Object.entries(data.result.results).map(([k, v]) => ({ agent: k, result: v as string }));
                setSwarmResults(newResults);
            }
            setState(prev => ({ ...prev, status: 'completed' }));
        }
    };

    const addLog = (msg: string) => {
        setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
    };

    const sendCommand = async (endpoint: string, body?: any) => {
        try {
            await fetch(`http://localhost:8000/${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
        } catch (e) {
            addLog(`System: Failed to send command ${endpoint}`);
        }
    };

    return (
        <div className="god-mode-container">
            <header className="header">
                <h1>PROJECT GREAT // GOD MODE</h1>
                <div className="header-right">
                    <div className="memory-pill">
                        🧠 MEM: {memoryStats.total_memories} | XP: {memoryStats.total_accumulated_experience}
                    </div>
                    <div className="status-badge" data-status={state.status}>
                        {state.status.toUpperCase()}
                    </div>
                </div>
            </header>

            <div className="main-grid">
                <div className="viewport-section">
                    {/* Main Visualizer - Swaps between Single View and Swarm Grid */}
                    <div className="viewport">
                        {state.status.includes('swarm') || swarmResults.length > 0 ? (
                            <div className="swarm-grid">
                                {swarmResults.length === 0 && state.status === 'swarm_started' && (
                                    <div className="swarm-loading">Deploying Agents...</div>
                                )}
                                {swarmResults.map((res, i) => (
                                    <div key={i} className="swarm-card fade-in">
                                        <h3>Agent: {res.agent.toUpperCase()}</h3>
                                        <div className="swarm-content">{res.result}</div>
                                        <div className="swarm-status">DONE</div>
                                    </div>
                                ))}
                                {/* Placeholders for visual effect if running */}
                                {state.status === 'swarm_started' && swarmResults.length < 3 && (
                                    <div className="swarm-card placeholder-agent">
                                        <h3>Allocating...</h3>
                                        <div className="loader"></div>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <>
                                {state.screenshot ? (
                                    <img
                                        src={`data:image/png;base64,${state.screenshot}`}
                                        alt="Live Browser Feed"
                                    />
                                ) : (
                                    <div className="placeholder">AWAITING VISUAL FEED...</div>
                                )}
                            </>
                        )}

                        <div className="overlay">
                            {state.status === 'running' && <span className="rec-indicator">● LIVE</span>}
                        </div>
                    </div>

                    <div className="controls">
                        <input
                            type="text"
                            value={inputTask}
                            onChange={e => setInputTask(e.target.value)}
                            placeholder="Enter directive..."
                        />
                        <button
                            className="btn-start"
                            onClick={() => sendCommand('agent/start', { task: inputTask || "Go to google.com" })}
                        >
                            SINGLE AGENT
                        </button>
                        <button
                            className="btn-swarm"
                            onClick={() => sendCommand('swarm/start', { task: inputTask || "Plan trip to Japan", mode: "simulate" })}
                        >
                            DEPLOY SWARM
                        </button>
                        <button
                            className="btn-pause"
                            onClick={() => sendCommand('agent/pause')}
                        >
                            FREEZE
                        </button>
                        <button
                            className="btn-resume"
                            onClick={() => sendCommand('agent/resume')}
                        >
                            RESUME
                        </button>
                        <button
                            className="btn-stop"
                            onClick={() => sendCommand('agent/stop')}
                        >
                            TERMINATE
                        </button>
                    </div>
                </div>

                <div className="neural-log" ref={logContainerRef}>
                    {logs.map((log, i) => (
                        <div key={i} className="log-entry">{log}</div>
                    ))}
                    {state.thoughts && (
                        <div className="thought-stream">
                            <span className="cursor">Processing: </span>{state.thoughts}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
