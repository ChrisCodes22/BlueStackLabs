# Blue Stack Labs Website

A modern, professional website for Blue Stack Labs software development company.

## 🚀 Quick Start

### Option 1: Deploy to Netlify (Easiest - Free)

1. Go to [Netlify](https://www.netlify.com/) and sign up for a free account
2. Click "Add new site" → "Deploy manually"
3. Drag and drop this entire folder into Netlify
4. Your site will be live in seconds with a free netlify.app domain
5. To use a custom domain (bluestacklabs.com):
   - Go to "Domain settings" in Netlify
   - Click "Add custom domain"
   - Follow instructions to point your domain to Netlify

### Option 2: Deploy to Vercel (Also Free)

1. Go to [Vercel](https://vercel.com/) and sign up
2. Click "Add New" → "Project"
3. Import this folder
4. Deploy - done!
5. Add custom domain in project settings

### Option 3: Traditional Hosting (Bluehost, HostGator, etc.)

1. Purchase hosting and domain name
2. Access your hosting control panel (cPanel)
3. Upload all files to the `public_html` folder using File Manager or FTP
4. Your site will be live at your domain

## 📧 Setting Up the Contact Form

The contact form currently uses Formspree (free service). To make it work:

1. Go to [Formspree.io](https://formspree.io/) and create a free account
2. Create a new form
3. Copy your form ID (looks like: `abc123xyz`)
4. Open `script.js` and replace `YOUR_FORM_ID` on line 29 with your actual form ID:
   ```javascript
   const response = await fetch('https://formspree.io/f/YOUR_ACTUAL_FORM_ID', {
   ```
5. Save and re-upload the file

**Alternative:** If you want emails to go directly to your email without Formspree:
- Replace the contact form button with: `<a href="mailto:info@bluestacklabs.com" class="btn btn-primary">Email Us</a>`

## 📁 Files Included

- `index.html` - Main website file
- `styles.css` - All styling
- `script.js` - Interactive features and form handling
- `netlify.toml` - Configuration for Netlify deployment
- `README.md` - This file

## 🎨 Customization

### Change Colors
Edit the CSS variables in `styles.css` (lines 1-10):
```css
:root {
    --primary-blue: #0066FF;    /* Main brand color */
    --deep-blue: #0047AB;       /* Darker blue */
    --light-blue: #00A3FF;      /* Lighter blue */
}
```

### Update Content
All content is in `index.html`. Simply search for the text you want to change and edit it.

### Add Social Links
In the footer section of `index.html`, add your actual social media URLs:
```html
<li><a href="https://linkedin.com/company/yourcompany">LinkedIn</a></li>
<li><a href="https://github.com/yourcompany">GitHub</a></li>
```

## 🔧 Need Help?

Contact: info@bluestacklabs.com

## 📝 License

© 2026 Blue Stack Labs. All rights reserved.
