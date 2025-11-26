// generate_pdf.js
const puppeteer = require('puppeteer');
const path = require('path');

// process.argv[0] is 'node'
// process.argv[1] is 'generate_pdf.js'
// We expect the input path at index 2 and output path at index 3.
const inputHtmlPath = process.argv[2];
const outputPdfPath = process.argv[3];

if (!inputHtmlPath || !outputPdfPath) {
    console.error('Usage: node generate_pdf.js <input.html> <output.pdf>');
    process.exit(1);
}

(async () => {
    let browser;
    try {
        browser = await puppeteer.launch();
        const page = await browser.newPage();

        // Resolve the input path to an absolute file URL for Puppeteer
        const absoluteHtmlPath = path.resolve(inputHtmlPath);
        
        // Go to the local HTML file
        await page.goto(`file://${absoluteHtmlPath}`, { waitUntil: 'networkidle0' });

        // Generate the PDF
        await page.pdf({ 
            path: outputPdfPath, 
            format: 'A4',
            printBackground: true, // Ensure background colors/images are included
        });

        console.log(`Successfully generated PDF: ${outputPdfPath}`);
        
    } catch (error) {
        console.error('An error occurred during PDF generation:', error);
        process.exit(1);
    } finally {
        if (browser) {
            await browser.close();
        }
    }
})();