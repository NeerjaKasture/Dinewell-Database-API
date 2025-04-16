document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("loginForm");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const username = document.getElementById("email").value;
      const password = document.getElementById("password").value;

      try {
        const res = await fetch("/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: username, password })  // Changed to 'email'
        });

        const data = await res.json();

        if (res.ok) {
          // Your existing token handling code
          
          // Note: The backend doesn't return a token field, it uses cookies
          // So this part needs adjustment too:
          if (data.user && data.user.role) {
            const role = data.user.role;
            
            if (role === "Student") window.location.href = "/student.html";
            else if (role === "Council") window.location.href = "/council.html";
            else if (role === "Employee") window.location.href = "/employee.html";
            else if (role === "Admin") window.location.href = "/admin.html";
            else document.getElementById("error").innerText = "Unknown role";
          } else {
            document.getElementById("error").innerText = "Invalid response format";
          }
        } else {
          document.getElementById("error").innerText = data.error || "Login failed";
        }
      } catch (err) {
        console.error(err);
        document.getElementById("error").innerText = "Server error";
      }
    });
  }
});
