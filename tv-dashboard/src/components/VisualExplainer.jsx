/**
 * VisualExplainer — renders AI-generated HTML/SVG content in a sandboxed iframe.
 */
export default function VisualExplainer({ visualData }) {
  if (!visualData) return null;

  const { topic, htmlContent } = visualData;

  // Wrap content in a full HTML document for the iframe
  const fullHtml = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {
          margin: 0;
          padding: 24px;
          background: #0a0e1a;
          color: #f8fafc;
          font-family: 'Inter', -apple-system, sans-serif;
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 100vh;
        }
      </style>
    </head>
    <body>
      ${htmlContent}
    </body>
    </html>
  `;

  return (
    <div className="visual-container">
      <iframe
        className="visual-iframe"
        srcDoc={fullHtml}
        title={`Visual: ${topic}`}
        sandbox="allow-scripts"
      />
    </div>
  );
}
