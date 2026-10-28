import { Link } from 'react-router-dom'
import { Logo } from '../components/ui'

export default function Privacy() {
  return (
    <div className="mx-auto max-w-3xl px-5 py-10">
      <Link to="/"><Logo /></Link>
      <h1 className="mt-8 font-serif text-3xl font-semibold">Privacy & Data Policy</h1>
      <div className="mt-6 space-y-5 text-ink-300 [&_h2]:mt-6 [&_h2]:font-semibold [&_h2]:text-ink-100">
        <p>AI-KEN helps you turn personal stories into poetry. We treat what you share with care.</p>
        <h2>What we store</h2>
        <p>Your name, email and a securely hashed password; your conversations, stories and poems; ratings you give; and basic security logs (sign-ins, password changes). We do not store payment information.</p>
        <h2>Who can see your stories</h2>
        <p>Only you. Administrators manage accounts and see aggregated statistics (for example, how many haiku were written this week), but the admin dashboard does not show your stories, messages or poems.</p>
        <h2>AI processing</h2>
        <p>To write a poem, your story is sent to the configured AI language-model provider over an encrypted connection. Emotion detection is an interpretation of your text, not a medical or psychological diagnosis.</p>
        <h2>Your controls</h2>
        <p>You can delete any poem or conversation, or all of your data at once from Profile → Delete my data. Deleting your account (ask an administrator) removes everything linked to it.</p>
        <h2>Retention</h2>
        <p>Content is kept until you delete it. Security logs are kept for audit purposes and never include passwords or story text.</p>
        <h2>If you are struggling</h2>
        <p>If you are going through something heavy, please reach out to someone you trust. In the Philippines, the NCMH Crisis Hotline is available 24/7 at 1553.</p>
      </div>
    </div>
  )
}
