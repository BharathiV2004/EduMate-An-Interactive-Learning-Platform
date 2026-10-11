import React from 'react';
import { ReactFlowProvider } from 'reactflow';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { MindMapCanvas } from './components/Canvas/MindMapCanvas';
import { Toolbar } from './components/Toolbar/Toolbar';
import { useMindMapStore } from './store/mindMapStore';

const App: React.FC = () => {
  const { userSettings } = useMindMapStore();

  const theme = createTheme({
    palette: {
      mode: userSettings.theme,
    },
  });

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <ReactFlowProvider>
        <div style={{ width: '100vw', height: '100vh', position: 'relative' }}>
          <MindMapCanvas />
          <Toolbar />
        </div>
      </ReactFlowProvider>
    </ThemeProvider>
  );
};

export default App; 