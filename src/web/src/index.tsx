import React from 'react';
import ReactDOM from 'react-dom';
import { CacheProvider } from 'rest-hooks';
import './index.css';
import 'react-virtualized/styles.css';
import App from './App';
import { BrowserRouter as Router } from 'react-router-dom';
import { positions, Provider as AlertProvider } from 'react-alert';

import AlertTemplate from 'react-alert-template-basic'

// React-pdf setup
import { pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.js`;



ReactDOM.render(
    <CacheProvider>
      <AlertProvider template={AlertTemplate} position={positions.BOTTOM_RIGHT}>
        <Router>
          <App />
        </Router>
      </AlertProvider>
    </CacheProvider>,
  document.getElementById('root')
);
