import React from 'react';
import ReactDOM from 'react-dom';
import { CacheProvider } from 'rest-hooks';
import './index.css';
import 'react-virtualized/styles.css';
import App from './App';
import { BrowserRouter as Router } from 'react-router-dom';

// React-pdf setup
import { pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.js`;

ReactDOM.render(
    <CacheProvider>
      <Router>
        <App />
      </Router>
    </CacheProvider>,
  document.getElementById('root')
);
