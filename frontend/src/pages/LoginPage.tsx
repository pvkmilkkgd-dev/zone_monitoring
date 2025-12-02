import { FormEvent, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { getCurrentUser, login } from "../auth";

export function LoginPage() {
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);

    if (!username.trim() || !password) {
      setError("�'�?��?��'�� ��?�? ���?�>�?���?�?���'��>�? �� �����?�?�>�?.");
      return;
    }

    setIsSubmitting(true);
    try {
      await login(username, password);

      const user = getCurrentUser();
      setMessage(`�"�?�+�?�? ���?����>�?�?���'�?, ${user?.username}!`);

      setTimeout(() => {
        navigate("/", { replace: true });
      }, 800);
    } catch (err) {
      console.error(err);
      setError(
        (err as Error).message ||
          "�?�� �?�?���>�?�?�? ���?�?��>�?�ؐ�'�?�?�? �� �?��?�?��?�?."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div style={{ padding: "16px" }}>
      <h1>Zone Monitoring</h1>
      <h2>�'�:�?�?</h2>

      <form onSubmit={handleSubmit} style={{ maxWidth: 400 }}>
        <div style={{ marginBottom: 8 }}>
          <label>
            �?�?�? ���?�>�?���?�?���'��>�?
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              style={{ display: "block", width: "100%" }}
              autoComplete="username"
            />
          </label>
        </div>

        <div style={{ marginBottom: 8 }}>
          <label>
            �?���?�?�>�?
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={{ display: "block", width: "100%" }}
              autoComplete="current-password"
            />
          </label>
        </div>

        {error && (
          <div style={{ color: "red", marginBottom: 8 }}>{error}</div>
        )}

        {message && (
          <div style={{ color: "green", marginBottom: 8 }}>{message}</div>
        )}

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "�'�:�?�?��?..." : "�'�?���'��"}
        </button>
      </form>

      <p style={{ marginTop: 16 }}>
        �?��' �?�ؑ'�'�?�?�� ��������?��?{" "}
        <Link to="/register">�-���?��?��?�'�?��?�?�?���'�?�?�?</Link>
      </p>
    </div>
  );
}
