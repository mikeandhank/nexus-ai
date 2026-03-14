export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { email } = req.body;
  if (!email) {
    return res.status(400).json({ error: 'Email is required' });
  }

  try {
    const response = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.RESEND_API_KEY}`
      },
      body: JSON.stringify({
        from: 'Nexus AI <waitlist@nexusai.com>',
        to: email,
        subject: 'You\'re on the Nexus AI Waitlist!',
        html: `
          <h2>Welcome to Nexus AI! 🚀</h2>
          <p>You're on the list. We'll be in touch soon with early access.</p>
          <p>In the meantime, tell us about your business needs:</p>
          <p>— What tasks would you most want to automate?</p>
          <hr>
          <p style="color: #666; font-size: 12px;">Nexus AI — Autonomous agents for SMBs</p>
        `
      })
    });

    if (!response.ok) {
      const err = await response.json();
      return res.status(400).json({ error: err.message });
    }

    return res.status(200).json({ success: true });
  } catch (error) {
    return res.status(500).json({ error: error.message });
  }
}
