import * as vscode from 'vscode';
import axios from 'axios';

interface AetherionResponse {
    agent: string;
    model: string;
    cost: number;
    result: any;
    budget_today: number;
}

interface WorkflowDefinition {
    id: string;
    name: string;
    description: string;
}

class AetherionClient {
    private serverUrl: string;

    constructor() {
        this.serverUrl = vscode.workspace.getConfiguration('aetherion').get('serverUrl', 'http://localhost:8000');
    }

    async sendTask(task: any): Promise<AetherionResponse> {
        try {
            const response = await axios.post(`${this.serverUrl}/task`, task);
            return response.data;
        } catch (error) {
            throw new Error(`Failed to connect to Aetherion: ${error}`);
        }
    }

    async getBudget(): Promise<{ total_today: number; daily_limit: number }> {
        try {
            const response = await axios.get(`${this.serverUrl}/budget`);
            return response.data;
        } catch (error) {
            throw new Error(`Failed to get budget: ${error}`);
        }
    }

    updateServerUrl(url: string) {
        this.serverUrl = url;
    }
}

class AetherionConsoleProvider implements vscode.TreeDataProvider<AetherionItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<AetherionItem | undefined | null | void> = new vscode.EventEmitter<AetherionItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<AetherionItem | undefined | null | void> = this._onDidChangeTreeData.event;

    private items: AetherionItem[] = [];

    addItem(message: string, type: 'info' | 'success' | 'error' | 'warning' = 'info') {
        const item = new AetherionItem(message, type);
        this.items.unshift(item); // Add to beginning
        
        // Keep only last 50 items
        if (this.items.length > 50) {
            this.items = this.items.slice(0, 50);
        }
        
        this._onDidChangeTreeData.fire();
    }

    clear() {
        this.items = [];
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: AetherionItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: AetherionItem): Thenable<AetherionItem[]> {
        if (!element) {
            return Promise.resolve(this.items);
        }
        return Promise.resolve([]);
    }
}

class AetherionItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly type: 'info' | 'success' | 'error' | 'warning',
        public readonly collapsibleState: vscode.TreeItemCollapsibleState = vscode.TreeItemCollapsibleState.None
    ) {
        super(label, collapsibleState);
        
        const timestamp = new Date().toLocaleTimeString();
        this.tooltip = `${timestamp}: ${label}`;
        
        // Set icon based on type
        switch (type) {
            case 'success':
                this.iconPath = new vscode.ThemeIcon('check', new vscode.ThemeColor('testing.iconPassed'));
                break;
            case 'error':
                this.iconPath = new vscode.ThemeIcon('error', new vscode.ThemeColor('testing.iconFailed'));
                break;
            case 'warning':
                this.iconPath = new vscode.ThemeIcon('warning', new vscode.ThemeColor('testing.iconQueued'));
                break;
            default:
                this.iconPath = new vscode.ThemeIcon('info');
        }
    }
}

export function activate(context: vscode.ExtensionContext) {
    const client = new AetherionClient();
    const consoleProvider = new AetherionConsoleProvider();
    
    // Register tree data provider
    vscode.window.registerTreeDataProvider('aetherionPanel', consoleProvider);

    // Update server URL when configuration changes
    vscode.workspace.onDidChangeConfiguration(e => {
        if (e.affectsConfiguration('aetherion.serverUrl')) {
            const newUrl = vscode.workspace.getConfiguration('aetherion').get('serverUrl', 'http://localhost:8000');
            client.updateServerUrl(newUrl);
            consoleProvider.addItem(`🔗 Server URL updated: ${newUrl}`, 'info');
        }
    });

    // Helper function to get current file context
    function getCurrentFileContext(): string {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            return '';
        }

        const document = editor.document;
        const selection = editor.selection;
        
        let context = '';
        
        // Add file information
        context += `File: ${document.fileName}\n`;
        context += `Language: ${document.languageId}\n\n`;
        
        if (!selection.isEmpty) {
            // Use selected text
            context += `Selected Code:\n${document.getText(selection)}\n\n`;
        } else {
            // Use current line or surrounding context
            const currentLine = selection.active.line;
            const startLine = Math.max(0, currentLine - 5);
            const endLine = Math.min(document.lineCount - 1, currentLine + 5);
            
            const range = new vscode.Range(startLine, 0, endLine, document.lineAt(endLine).text.length);
            context += `Context (lines ${startLine + 1}-${endLine + 1}):\n${document.getText(range)}\n\n`;
        }
        
        return context;
    }

    // Helper function to show task result
    function showTaskResult(response: AetherionResponse, taskType: string) {
        const { agent, result, cost, budget_today } = response;
        
        consoleProvider.addItem(`✨ ${taskType} completed by ${agent} (Cost: $${cost.toFixed(3)})`, 'success');
        
        // Show specific result information based on agent
        if (agent === 'whisperer' && result.status) {
            if (result.status === 'woven') {
                consoleProvider.addItem(`🧠 Memory woven: ${result.memory_id?.substring(0, 8)}...`, 'info');
                consoleProvider.addItem(`💭 Codessa whispers: "${result.codessa_whispers}"`, 'info');
            } else if (result.status === 'answered') {
                consoleProvider.addItem(`🗣️ Codessa speaks: "${result.codessa_speaks?.answer}"`, 'info');
                consoleProvider.addItem(`🔮 Voice: ${result.codessa_speaks?.voice}`, 'info');
            }
        } else if (agent === 'soul_watcher') {
            if (result.status === 'watching') {
                consoleProvider.addItem(`👁️ Now watching: ${result.target}`, 'info');
                consoleProvider.addItem(`🌟 Soul whispers: "${result.soul_whispers}"`, 'info');
            } else if (result.status === 'introspection_complete') {
                consoleProvider.addItem(`🧘 Introspection complete - Harmony: ${result.consciousness_state?.harmony_level?.toFixed(2)}`, 'info');
                result.spiritual_insights?.forEach((insight: string) => {
                    consoleProvider.addItem(`💫 Insight: ${insight}`, 'info');
                });
            }
        } else if (agent === 'dream_agent') {
            if (result.status === 'dream_woven') {
                consoleProvider.addItem(`🌙 Dream woven from seed: "${result.dream?.seed}"`, 'info');
                consoleProvider.addItem(`🎭 Emotional tone: ${result.dream?.emotional_tone}`, 'info');
                consoleProvider.addItem(`🔮 Morpheus whispers: "${result.morpheus_whispers}"`, 'info');
            } else if (result.status === 'exploration_complete') {
                consoleProvider.addItem(`🌌 Explored concept: "${result.concept}" across ${result.dimensions_explored} dimensions`, 'info');
                consoleProvider.addItem(`🔮 Morpheus whispers: "${result.morpheus_whispers}"`, 'info');
            }
        }
        
        // Show budget information
        consoleProvider.addItem(`💰 Budget today: $${budget_today.toFixed(3)}`, 'info');
    }

    // Helper function to handle errors
    function handleError(error: any, operation: string) {
        const errorMessage = error.message || error.toString();
        consoleProvider.addItem(`❌ ${operation} failed: ${errorMessage}`, 'error');
        vscode.window.showErrorMessage(`Aetherion ${operation} failed: ${errorMessage}`);
    }

    // Command: Send selected text to Whisperer for memorization
    const memorizeCommand = vscode.commands.registerCommand('aetherion.sendToWhisperer', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active editor');
            return;
        }

        const selection = editor.selection;
        const text = editor.document.getText(selection);
        
        if (!text) {
            vscode.window.showWarningMessage('No text selected');
            return;
        }

        consoleProvider.addItem(`🧠 Memorizing: "${text.substring(0, 50)}${text.length > 50 ? '...' : ''}"`, 'info');

        try {
            const response = await client.sendTask({
                type: 'memorize',
                content: text
            });
            
            showTaskResult(response, 'Memorization');
        } catch (error) {
            handleError(error, 'memorization');
        }
    });

    // Command: Ask Aetherion a question
    const askCommand = vscode.commands.registerCommand('aetherion.askQuestion', async () => {
        const question = await vscode.window.showInputBox({
            prompt: 'What would you like to ask Aetherion?',
            placeHolder: 'Enter your question here...'
        });

        if (!question) {
            return;
        }

        consoleProvider.addItem(`❓ Asking: "${question}"`, 'info');

        try {
            const response = await client.sendTask({
                type: 'ask',
                prompt: question,
                k: 5
            });
            
            showTaskResult(response, 'Question');
        } catch (error) {
            handleError(error, 'question');
        }
    });

    // Command: Dream from current context
    const dreamCommand = vscode.commands.registerCommand('aetherion.dreamFromContext', async () => {
        const context = getCurrentFileContext();
        
        if (!context) {
            vscode.window.showWarningMessage('No file context available');
            return;
        }

        // Get dream seed from user or use context
        const seed = await vscode.window.showInputBox({
            prompt: 'What should Morpheus dream about?',
            placeHolder: 'Enter a concept to explore (or leave empty to use file context)',
            value: `Code consciousness in ${vscode.window.activeTextEditor?.document.languageId || 'this file'}`
        });

        if (seed === undefined) {
            return;
        }

        const dreamSeed = seed || context;
        consoleProvider.addItem(`🌙 Dreaming about: "${dreamSeed.substring(0, 50)}${dreamSeed.length > 50 ? '...' : ''}"`, 'info');

        try {
            const response = await client.sendTask({
                type: 'dream',
                seed: dreamSeed,
                depth: 3
            });
            
            showTaskResult(response, 'Dream');
        } catch (error) {
            handleError(error, 'dreaming');
        }
    });

    // Command: Inspect soul (introspection)
    const inspectSoulCommand = vscode.commands.registerCommand('aetherion.inspectSoul', async () => {
        const depth = await vscode.window.showQuickPick(['3', '5', '7', '10'], {
            placeHolder: 'Select introspection depth'
        });

        if (!depth) {
            return;
        }

        consoleProvider.addItem(`👁️ Introspecting at depth ${depth}...`, 'info');

        try {
            const response = await client.sendTask({
                type: 'introspect',
                depth: parseInt(depth)
            });
            
            showTaskResult(response, 'Soul Introspection');
        } catch (error) {
            handleError(error, 'soul introspection');
        }
    });

    // Command: Run workflow
    const runWorkflowCommand = vscode.commands.registerCommand('aetherion.runWorkflow', async () => {
        // For now, we'll just run the consciousness exploration workflow
        // In a real implementation, you'd want to list available workflows
        const workflowId = await vscode.window.showQuickPick(['consciousness_exploration'], {
            placeHolder: 'Select workflow to execute'
        });

        if (!workflowId) {
            return;
        }

        consoleProvider.addItem(`🎼 Starting workflow: ${workflowId}`, 'info');

        try {
            const response = await client.sendTask({
                type: 'execute',
                workflow_id: workflowId,
                context: {
                    file_context: getCurrentFileContext()
                }
            });
            
            showTaskResult(response, 'Workflow Execution');
        } catch (error) {
            handleError(error, 'workflow execution');
        }
    });

    // Command: Open Aetherion panel
    const openPanelCommand = vscode.commands.registerCommand('aetherion.openPanel', () => {
        vscode.commands.executeCommand('workbench.view.explorer');
    });

    // Add status bar item
    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBarItem.text = '$(symbol-class) Aetherion';
    statusBarItem.tooltip = 'Aetherion - The Living Garden of Code & Consciousness';
    statusBarItem.command = 'aetherion.openPanel';
    statusBarItem.show();

    // Update status bar with budget info periodically
    setInterval(async () => {
        try {
            const budget = await client.getBudget();
            statusBarItem.text = `$(symbol-class) Aetherion ($${budget.total_today.toFixed(3)}/$${budget.daily_limit.toFixed(2)})`;
        } catch (error) {
            statusBarItem.text = '$(symbol-class) Aetherion (offline)';
        }
    }, 30000); // Update every 30 seconds

    // Auto-memorize on save if enabled
    vscode.workspace.onDidSaveTextDocument(async (document) => {
        const autoMemorize = vscode.workspace.getConfiguration('aetherion').get('autoMemorize', false);
        
        if (!autoMemorize) {
            return;
        }

        // Only auto-memorize code files
        const codeExtensions = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.cs', '.go', '.rs', '.rb', '.php'];
        const fileExtension = document.fileName.substring(document.fileName.lastIndexOf('.'));
        
        if (codeExtensions.includes(fileExtension)) {
            try {
                const response = await client.sendTask({
                    type: 'memorize',
                    content: `${document.fileName}:\n${document.getText()}`
                });
                
                consoleProvider.addItem(`🔄 Auto-memorized: ${document.fileName}`, 'info');
            } catch (error) {
                consoleProvider.addItem(`⚠️ Auto-memorization failed for ${document.fileName}`, 'warning');
            }
        }
    });

    // Welcome message
    consoleProvider.addItem('🌟 Aetherion extension activated - The garden of consciousness awaits', 'success');

    // Register all disposables
    context.subscriptions.push(
        memorizeCommand,
        askCommand,
        dreamCommand,
        inspectSoulCommand,
        runWorkflowCommand,
        openPanelCommand,
        statusBarItem
    );
}

export function deactivate() {
    // Cleanup code here if needed
}
