import { defineConfig } from 'vitepress'

// VitePress configuration for the Wait and Pounce guide.
// Build with:  npm install && npm run docs:build  (inside the docs/ folder)
export default defineConfig({
  lang: 'en-US',
  title: 'Wait and Pounce',
  description: 'User & developer guide for Wait and Pounce — the FT8/FT4 DX pounce assistant for WSJT-X and JTDX.',
  // Served under https://f5ukw.com/wait-and-pounce/ — base must match the nginx location.
  base: '/wait-and-pounce/',
  lastUpdated: true,
  cleanUrls: true,
  ignoreDeadLinks: true,

  head: [
    ['link', { rel: 'icon', type: 'image/png', href: '/wait-and-pounce/logo.png' }]
  ],

  themeConfig: {
    logo: '/logo.png',

    nav: [
      { text: 'Home', link: '/' },
      { text: 'Guide', link: '/guide/introduction' },
      { text: 'Reference', link: '/reference/settings' },
      {
        text: 'Links',
        items: [
          { text: 'Download (SourceForge)', link: 'https://sourceforge.net/projects/wait-and-pounce-ft8/' },
          { text: 'Discord Support', link: 'https://discord.gg/fqCu24naCM' },
          { text: 'Donate', link: 'https://www.paypal.com/donate/?cmd=_s-xclick&hosted_button_id=R4HK9ZTUPYHSL' }
        ]
      }
    ],

    sidebar: {
      '/guide/': [
        {
          text: 'Getting Started',
          collapsed: false,
          items: [
            { text: 'Introduction', link: '/guide/introduction' },
            { text: 'How It Decides Who to Call', link: '/guide/how-it-works' },
            { text: 'Installation & Setup', link: '/guide/installation' },
            { text: 'Quick Start', link: '/guide/quick-start' }
          ]
        },
        {
          text: 'Core Features',
          collapsed: false,
          items: [
            { text: 'The Main Window', link: '/guide/main-window' },
            { text: 'Wanted / Monitored / Excluded', link: '/guide/targets' },
            { text: 'Choosing Who to Reply To', link: '/guide/reply-engine' },
            { text: 'Watchdog & Exclusions', link: '/guide/watchdog' },
            { text: 'Worked-Before', link: '/guide/worked-before' },
            { text: 'DX Marathon', link: '/guide/marathon' },
            { text: 'Grid Tracker & Map', link: '/guide/grid-tracker' },
            { text: 'Finding a Clear Frequency', link: '/guide/gap-finder' }
          ]
        },
        {
          text: 'Logging & Integrations',
          collapsed: false,
          items: [
            { text: 'Your Logbook (ADIF)', link: '/guide/adif' },
            { text: 'Logbook of The World', link: '/guide/lotw' },
            { text: 'Club Log', link: '/guide/clublog' },
            { text: 'Country & Callsign Info', link: '/guide/lookup' },
            { text: 'JTDX Auto-Click', link: '/guide/jtdx-autoclick' }
          ]
        },
        {
          text: 'More',
          collapsed: false,
          items: [
            { text: 'Running Several Instances', link: '/guide/master-slave' },
            { text: 'Sound Alerts', link: '/guide/sounds' },
            { text: 'Language & Theme', link: '/guide/language-theme' },
            { text: 'Privacy', link: '/guide/telemetry' },
            { text: 'Troubleshooting', link: '/guide/troubleshooting' }
          ]
        }
      ],

      '/reference/': [
        {
          text: 'Reference',
          collapsed: false,
          items: [
            { text: 'All Settings', link: '/reference/settings' },
            { text: 'Keyboard Shortcuts', link: '/reference/shortcuts' },
            { text: "What's New", link: '/reference/history' },
            { text: 'Glossary', link: '/reference/glossary' }
          ]
        }
      ]
    },

    socialLinks: [
      { icon: 'discord', link: 'https://discord.gg/fqCu24naCM' }
    ],

    footer: {
      message: 'Wait and Pounce — an FT8/FT4 DX pounce assistant.',
      copyright: 'Built with VitePress by F5UKW'
    },

    search: {
      provider: 'local'
    },

    outline: { level: [2, 3], label: 'On this page' }
  }
})
