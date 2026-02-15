import React, { useState, useEffect, useCallback } from 'react';
import {
  ThemeProvider,
  createTheme,
  CssBaseline,
  Box,
  AppBar,
  Toolbar,
  Typography,
  Container,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Chip,
  Alert,
  Snackbar,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  Paper,
  Fab,
} from '@mui/material';
import {
  Add as AddIcon,
  CloudUpload as UploadIcon,
  School as TrainIcon,
  Chat as ChatIcon,
  Delete as DeleteIcon,
  InsertDriveFile as FileIcon,
  Refresh as RefreshIcon,
  SmartToy as BotIcon,
} from '@mui/icons-material';
import axios from 'axios';

// Dark theme with coral accent
const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#e94560',
    },
    secondary: {
      main: '#ff6b6b',
    },
    background: {
      default: '#0f0f1a',
      paper: '#1a1a2e',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          border: '1px solid rgba(255,255,255,0.1)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 600,
        },
      },
    },
  },
});

// API base URL
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(false);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [selectedApp, setSelectedApp] = useState(null);
  const [filesDialogOpen, setFilesDialogOpen] = useState(false);
  const [newAppId, setNewAppId] = useState('');
  const [newAppName, setNewAppName] = useState('');
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [files, setFiles] = useState([]);
  const [training, setTraining] = useState({});

  // Fetch apps
  const fetchApps = useCallback(async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/api/apps`);
      setApps(response.data.data || []);
    } catch (error) {
      showSnackbar('Failed to fetch apps', 'error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchApps();
  }, [fetchApps]);

  // Show snackbar
  const showSnackbar = (message, severity = 'success') => {
    setSnackbar({ open: true, message, severity });
  };

  // Create app
  const handleCreateApp = async () => {
    if (!newAppId || !newAppName) {
      showSnackbar('Please fill in all fields', 'error');
      return;
    }

    try {
      await axios.post(`${API_URL}/api/apps`, {
        appId: newAppId,
        name: newAppName,
      });
      showSnackbar(`App "${newAppName}" created successfully!`);
      setCreateDialogOpen(false);
      setNewAppId('');
      setNewAppName('');
      fetchApps();
    } catch (error) {
      showSnackbar(error.response?.data?.detail || 'Failed to create app', 'error');
    }
  };

  // Delete app
  const handleDeleteApp = async (appId) => {
    if (!window.confirm(`Are you sure you want to delete "${appId}"?`)) return;

    try {
      await axios.delete(`${API_URL}/api/apps/${appId}`);
      showSnackbar(`App "${appId}" deleted`);
      fetchApps();
    } catch (error) {
      showSnackbar('Failed to delete app', 'error');
    }
  };

  // Open files dialog
  const handleOpenFiles = async (app) => {
    setSelectedApp(app);
    setFilesDialogOpen(true);
    await fetchFiles(app.app_id);
  };

  // Fetch files for app
  const fetchFiles = async (appId) => {
    try {
      const response = await axios.get(`${API_URL}/api/apps/${appId}/files`);
      setFiles(response.data.data || []);
    } catch (error) {
      showSnackbar('Failed to fetch files', 'error');
    }
  };

  // Upload files
  const handleUploadFiles = async (event) => {
    const uploadedFiles = event.target.files;
    if (!uploadedFiles.length || !selectedApp) return;

    const formData = new FormData();
    for (let i = 0; i < uploadedFiles.length; i++) {
      formData.append('files', uploadedFiles[i]);
    }

    try {
      const response = await axios.post(
        `${API_URL}/api/apps/${selectedApp.app_id}/files`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      showSnackbar(`Uploaded ${response.data.data.uploaded.length} file(s)`);
      fetchFiles(selectedApp.app_id);
      fetchApps();
    } catch (error) {
      showSnackbar('Failed to upload files', 'error');
    }
  };

  // Train app
  const handleTrain = async (appId) => {
    setTraining((prev) => ({ ...prev, [appId]: true }));

    try {
      const response = await axios.post(`${API_URL}/api/apps/${appId}/train`);
      showSnackbar(
        `Training complete! ${response.data.data.documents} docs, ${response.data.data.chunks} chunks`
      );
      fetchApps();
    } catch (error) {
      showSnackbar(error.response?.data?.detail || 'Training failed', 'error');
    } finally {
      setTraining((prev) => ({ ...prev, [appId]: false }));
    }
  };

  // Open chat
  const handleOpenChat = (appId) => {
    window.open(`${API_URL}/chat?appId=${appId}`, '_blank');
  };

  // Get status color
  const getStatusColor = (status) => {
    switch (status) {
      case 'READY':
        return 'success';
      case 'INDEXING':
        return 'warning';
      case 'FAILED':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
        {/* App Bar */}
        <AppBar position="static" sx={{ bgcolor: 'background.paper', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
          <Toolbar>
            <BotIcon sx={{ mr: 2, color: 'primary.main' }} />
            <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 700 }}>
              Multi-App RAG Dashboard
            </Typography>
            <IconButton color="inherit" onClick={fetchApps}>
              <RefreshIcon />
            </IconButton>
          </Toolbar>
        </AppBar>

        {loading && <LinearProgress color="primary" />}

        <Container maxWidth="lg" sx={{ py: 4 }}>
          {/* Header */}
          <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box>
              <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
                Your Apps
              </Typography>
              <Typography variant="body1" color="text.secondary">
                Create apps, upload documents, train, and chat with your knowledge base
              </Typography>
            </Box>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setCreateDialogOpen(true)}
              size="large"
            >
              Create App
            </Button>
          </Box>

          {/* Apps Grid */}
          {apps.length === 0 ? (
            <Paper
              sx={{
                p: 6,
                textAlign: 'center',
                bgcolor: 'background.paper',
                borderRadius: 4,
              }}
            >
              <BotIcon sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
              <Typography variant="h5" sx={{ mb: 1 }}>
                No apps yet
              </Typography>
              <Typography color="text.secondary" sx={{ mb: 3 }}>
                Create your first app to get started
              </Typography>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={() => setCreateDialogOpen(true)}
              >
                Create App
              </Button>
            </Paper>
          ) : (
            <Grid container spacing={3}>
              {apps.map((app) => (
                <Grid item xs={12} sm={6} md={4} key={app.app_id}>
                  <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                    <CardContent sx={{ flexGrow: 1 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>
                          {app.name}
                        </Typography>
                        <Chip
                          label={app.status}
                          size="small"
                          color={getStatusColor(app.status)}
                        />
                      </Box>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        ID: {app.app_id}
                      </Typography>
                      {app.last_indexed_at && (
                        <Typography variant="caption" color="text.secondary">
                          Last trained: {new Date(app.last_indexed_at).toLocaleString()}
                        </Typography>
                      )}
                    </CardContent>
                    <Divider />
                    <CardActions sx={{ p: 2, gap: 1 }}>
                      <Button
                        size="small"
                        startIcon={<UploadIcon />}
                        onClick={() => handleOpenFiles(app)}
                      >
                        Files
                      </Button>
                      <Button
                        size="small"
                        startIcon={<TrainIcon />}
                        onClick={() => handleTrain(app.app_id)}
                        disabled={training[app.app_id]}
                        color="secondary"
                      >
                        {training[app.app_id] ? 'Training...' : 'Train'}
                      </Button>
                      <Button
                        size="small"
                        startIcon={<ChatIcon />}
                        onClick={() => handleOpenChat(app.app_id)}
                        disabled={app.status !== 'READY'}
                        color="primary"
                      >
                        Chat
                      </Button>
                      <IconButton
                        size="small"
                        onClick={() => handleDeleteApp(app.app_id)}
                        sx={{ ml: 'auto' }}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </CardActions>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}
        </Container>

        {/* Create App Dialog */}
        <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
          <DialogTitle>Create New App</DialogTitle>
          <DialogContent>
            <TextField
              autoFocus
              margin="dense"
              label="App ID"
              fullWidth
              variant="outlined"
              value={newAppId}
              onChange={(e) => setNewAppId(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
              helperText="Letters, numbers, and dashes only (e.g., css, bes-system)"
              sx={{ mb: 2 }}
            />
            <TextField
              margin="dense"
              label="App Name"
              fullWidth
              variant="outlined"
              value={newAppName}
              onChange={(e) => setNewAppName(e.target.value)}
              helperText="Display name for the app"
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleCreateApp} variant="contained">
              Create
            </Button>
          </DialogActions>
        </Dialog>

        {/* Files Dialog */}
        <Dialog
          open={filesDialogOpen}
          onClose={() => setFilesDialogOpen(false)}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle>
            {selectedApp?.name} - Files
          </DialogTitle>
          <DialogContent>
            <Box sx={{ mb: 2 }}>
              <input
                accept=".txt,.md"
                style={{ display: 'none' }}
                id="file-upload"
                multiple
                type="file"
                onChange={handleUploadFiles}
              />
              <label htmlFor="file-upload">
                <Button
                  variant="outlined"
                  component="span"
                  startIcon={<UploadIcon />}
                  fullWidth
                >
                  Upload Files (.txt, .md)
                </Button>
              </label>
            </Box>
            <Divider sx={{ my: 2 }} />
            {files.length === 0 ? (
              <Typography color="text.secondary" align="center" sx={{ py: 4 }}>
                No files uploaded yet
              </Typography>
            ) : (
              <List>
                {files.map((file) => (
                  <ListItem key={file.id}>
                    <ListItemIcon>
                      <FileIcon />
                    </ListItemIcon>
                    <ListItemText
                      primary={file.filename}
                      secondary={`${(file.file_size / 1024).toFixed(1)} KB • ${new Date(
                        file.uploaded_at
                      ).toLocaleDateString()}`}
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setFilesDialogOpen(false)}>Close</Button>
          </DialogActions>
        </Dialog>

        {/* Snackbar */}
        <Snackbar
          open={snackbar.open}
          autoHideDuration={4000}
          onClose={() => setSnackbar({ ...snackbar, open: false })}
        >
          <Alert
            onClose={() => setSnackbar({ ...snackbar, open: false })}
            severity={snackbar.severity}
            sx={{ width: '100%' }}
          >
            {snackbar.message}
          </Alert>
        </Snackbar>
      </Box>
    </ThemeProvider>
  );
}

export default App;

