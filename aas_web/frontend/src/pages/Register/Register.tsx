import { useState, useEffect } from "react";
import Sidebar from "../../components/Sidebar/Sidebar.jsx";
import layout from "../ProductionHub/AAS_ScaraMonitoringHub.module.css";
import styles from "./Register.module.css";
import { listUsers, registerUser, updateUser, type UserRead, type UserCreate, type UserUpdate } from "../../services/userApi";
import SearchableSelect from "../../components/ui/SearchableSelect";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "../../components/lightswind/table";

export default function Register() {
    const [users, setUsers] = useState<UserRead[]>([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [editingUser, setEditingUser] = useState<UserRead | null>(null);

    const [formData, setFormData] = useState<UserCreate>({
        username: "",
        email: "",
        full_name: "",
        password: "",
        department: "",
        role: "staff",
        profile_type: "user"
    });

    const [confirmPassword, setConfirmPassword] = useState("");
    const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
    const [errors, setErrors] = useState<Record<string, string>>({});

    // Helper function to get user initials
    const getUserInitials = (fullName: string) => {
        const names = fullName.trim().split(" ");
        if (names.length === 1) return names[0].charAt(0).toUpperCase();
        return (names[0].charAt(0) + names[names.length - 1].charAt(0)).toUpperCase();
    };

    // Helper function to format last active time
    const getLastActive = (user: UserRead) => {
        // Since we don't have last_active in the API, we'll simulate it
        // In production, this would come from the user object
        if (!user.is_active) return "Never";

        // Simulate different last active states
        const randomStates = ["Just now", "2 hours ago", "3 days ago", "1 week ago"];
        return randomStates[user.id % randomStates.length];
    };

    // Helper function to get status text
    const getStatusText = (user: UserRead) => {
        if (user.is_active) return "Active";
        // Could add more statuses like "Pending" in the future
        return "Inactive";
    };

    useEffect(() => {
        loadUsers();
    }, []);

    const loadUsers = async () => {
        try {
            setLoading(true);
            const data = await listUsers();
            setUsers(data.users);
        } catch (error) {
            console.error("Erro ao carregar usuários:", error);
        } finally {
            setLoading(false);
        }
    };

    const validateForm = (): boolean => {
        const newErrors: Record<string, string> = {};

        if (formData.username.length < 3) {
            newErrors.username = "Username deve ter no mínimo 3 caracteres";
        }

        if (formData.full_name.length < 3) {
            newErrors.full_name = "Nome completo deve ter no mínimo 3 caracteres";
        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(formData.email)) {
            newErrors.email = "Email inválido";
        }

        // Senha é obrigatória apenas na criação
        if (!editingUser && formData.password.length < 8) {
            newErrors.password = "Senha deve ter no mínimo 8 caracteres";
        }

        // Se preencheu senha na edição, valida tamanho
        if (editingUser && formData.password && formData.password.length < 8) {
            newErrors.password = "Senha deve ter no mínimo 8 caracteres";
        }

        if (formData.password !== confirmPassword) {
            newErrors.confirmPassword = "Senhas não coincidem";
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleEdit = (user: UserRead) => {
        setEditingUser(user);
        setFormData({
            username: user.username,
            email: user.email,
            full_name: user.full_name,
            password: "", // Senha vazia na edição
            department: user.department || "",
            role: user.role || "staff",
            profile_type: user.profile_type || "user"
        });
        setConfirmPassword("");
        setErrors({});
        setShowModal(true);
    };

    const handleNewUser = () => {
        setEditingUser(null);
        setFormData({
            username: "",
            email: "",
            full_name: "",
            password: "",
            department: "",
            role: "staff",
            profile_type: "user"
        });
        setConfirmPassword("");
        setErrors({});
        setShowModal(true);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setMessage(null);

        if (!validateForm()) {
            return;
        }

        try {
            if (editingUser) {
                // Atualização
                const updateData: UserUpdate = {
                    full_name: formData.full_name,
                    email: formData.email,
                    department: formData.department,
                    role: formData.role,
                    profile_type: formData.profile_type
                };

                if (formData.password) {
                    updateData.password = formData.password;
                }

                await updateUser(editingUser.id, updateData);
                setMessage({
                    type: "success",
                    text: "Usuário atualizado com sucesso!",
                });
            } else {
                // Criação
                await registerUser(formData);
                setMessage({
                    type: "success",
                    text: "Usuário registrado com sucesso!",
                });
            }

            await loadUsers();

            setTimeout(() => {
                setShowModal(false);
                setMessage(null);
                setEditingUser(null);
            }, 1500);
        } catch (error) {
            setMessage({
                type: "error",
                text: error instanceof Error ? error.message : "Erro ao salvar usuário",
            });
        }
    };

    const handleToggleStatus = async (user: UserRead) => {
        try {
            await updateUser(user.id, { is_active: !user.is_active });
            await loadUsers();
        } catch (error) {
            console.error("Erro ao alternar status:", error);
        }
    };

    const handleChange = (field: keyof UserCreate, value: string) => {
        setFormData((prev) => ({ ...prev, [field]: value }));
        if (errors[field]) {
            setErrors((prev) => {
                const newErrors = { ...prev };
                delete newErrors[field];
                return newErrors;
            });
        }
    };

    return (
        <div className={layout.wrapper}>
            <Sidebar />

            <main className={layout.content}>
                <header className={layout.header}>
                    <h1 className={`${layout.pageTitle} ${styles.registerTitle}`}>
                        Registro de Usuários
                    </h1>
                </header>
                <div className={styles.actionBar}>
                    <button className={styles.newUserButton} onClick={handleNewUser}>
                        Novo Usuário
                    </button>
                </div>

                <section className={styles.tableSection}>
                    {loading ? (
                        <h1 className={`${layout.pageTitle} ${styles.registerTitle}`}>
                            Carregando usuários...
                        </h1>
                    ) : (
                        <>
                            <Table className={styles.userTable}>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>User</TableHead>
                                        <TableHead>Role</TableHead>
                                        <TableHead>Authorization</TableHead>
                                        <TableHead>Status</TableHead>
                                        <TableHead>Last Active</TableHead>
                                        <TableHead>Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {users.map((user) => (
                                        <TableRow key={user.id}>
                                            <TableCell>
                                                <div className={styles.userCell}>
                                                    <div className={styles.userAvatar}>
                                                        {getUserInitials(user.full_name)}
                                                    </div>
                                                    <div className={styles.userInfo}>
                                                        <div className={styles.userName}>{user.full_name}</div>
                                                        <div className={styles.userEmail}>{user.email}</div>
                                                    </div>
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <span className={styles.roleText}>
                                                    {user.role ? user.role.charAt(0).toUpperCase() + user.role.slice(1) : "Staff"}
                                                </span>
                                            </TableCell>
                                            <TableCell>
                                                <span className={`${styles.authBadge} ${user.profile_type === 'admin' ? styles.authAdmin : styles.authUser}`}>
                                                    {user.profile_type ? user.profile_type.charAt(0).toUpperCase() + user.profile_type.slice(1) : "User"}
                                                </span>
                                            </TableCell>
                                            <TableCell>
                                                <span className={`${styles.statusBadge} ${user.is_active ? styles.statusActive : styles.statusInactive}`}>
                                                    {getStatusText(user)}
                                                </span>
                                            </TableCell>
                                            <TableCell>
                                                <span className={styles.lastActive}>
                                                    {getLastActive(user)}
                                                </span>
                                            </TableCell>
                                            <TableCell>
                                                <div className={styles.actionsCell}>
                                                    <button
                                                        className={styles.actionIcon}
                                                        onClick={() => handleEdit(user)}
                                                        title="Editar usuário"
                                                    >
                                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                            <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path>
                                                        </svg>
                                                    </button>
                                                    <button
                                                        className={`${styles.actionIcon} ${styles.deleteIcon}`}
                                                        onClick={() => handleToggleStatus(user)}
                                                        title={user.is_active ? "Desativar usuário" : "Ativar usuário"}
                                                    >
                                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                            <line x1="18" y1="6" x2="6" y2="18"></line>
                                                            <line x1="6" y1="6" x2="18" y2="18"></line>
                                                        </svg>
                                                    </button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                            <div className={styles.tableFooter}>
                                <div className={styles.footerInfo}>
                                    Showing {users.length} of {users.length} users
                                </div>
                                <div className={styles.footerActions}>
                                    <button className={styles.footerButton} disabled>Previous</button>
                                    <button className={styles.footerButton} disabled>Next</button>
                                </div>
                            </div>
                        </>
                    )
                    }
                </section >

                {showModal && (
                    <div className={styles.modalOverlay} onClick={() => setShowModal(false)}>
                        <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
                            <div className={styles.modalHeader}>
                                <h2>{editingUser ? "Editar Usuário" : "Novo Usuário"}</h2>
                                <button className={styles.closeButton} onClick={() => setShowModal(false)}>
                                    ×
                                </button>
                            </div>

                            {message && (
                                <div className={`${styles.message} ${styles[message.type]}`}>
                                    {message.text}
                                </div>
                            )}

                            <form onSubmit={handleSubmit} className={styles.form}>
                                <div className={styles.formGrid}>
                                    <div className={styles.formGroup}>
                                        <label htmlFor="full_name">Nome Completo *</label>
                                        <input
                                            type="text"
                                            id="full_name"
                                            value={formData.full_name}
                                            onChange={(e) => handleChange("full_name", e.target.value)}
                                            className={errors.full_name ? styles.inputError : ""}
                                            required
                                        />
                                        {errors.full_name && <span className={styles.error}>{errors.full_name}</span>}
                                    </div>

                                    <div className={styles.formGroup}>
                                        <label htmlFor="username">Username *</label>
                                        <input
                                            type="text"
                                            id="username"
                                            value={formData.username}
                                            onChange={(e) => handleChange("username", e.target.value)}
                                            className={errors.username ? styles.inputError : ""}
                                            required
                                            disabled={!!editingUser}
                                        />
                                        {errors.username && <span className={styles.error}>{errors.username}</span>}
                                    </div>

                                    <div className={styles.formGroup}>
                                        <label htmlFor="email">Email *</label>
                                        <input
                                            type="email"
                                            id="email"
                                            value={formData.email}
                                            onChange={(e) => handleChange("email", e.target.value)}
                                            className={errors.email ? styles.inputError : ""}
                                            required
                                        />
                                        {errors.email && <span className={styles.error}>{errors.email}</span>}
                                    </div>

                                    <div className={styles.formGroup}>
                                        <label htmlFor="department">Department</label>
                                        <input
                                            type="text"
                                            id="department"
                                            value={formData.department || ""}
                                            onChange={(e) => handleChange("department", e.target.value)}
                                        />
                                    </div>

                                    <div className={styles.formGroup}>
                                        <label>Role *</label>
                                        <SearchableSelect
                                            options={[
                                                { value: "staff", label: "Staff" },
                                                { value: "manager", label: "Manager" },
                                                { value: "operator", label: "Operator" },
                                                { value: "director", label: "Director" }
                                            ]}
                                            value={formData.role ?? ""}
                                            onChange={(value) => handleChange("role", value)}
                                            placeholder="Selecione uma Role"
                                        />
                                    </div>

                                    <div className={styles.formGroup}>
                                        <label>Profile Type *</label>
                                        <SearchableSelect
                                            options={[
                                                { value: "user", label: "User" },
                                                { value: "admin", label: "Admin" }
                                            ]}
                                            value={formData.profile_type ?? ""}
                                            onChange={(value) => handleChange("profile_type", value)}
                                            placeholder="Selecione um Profile"
                                        />
                                    </div>

                                    <div className={styles.formGroup}>
                                        <label htmlFor="password">
                                            {editingUser ? "Nova Senha (opcional)" : "Senha *"}
                                        </label>
                                        <input
                                            type="password"
                                            id="password"
                                            value={formData.password}
                                            onChange={(e) => handleChange("password", e.target.value)}
                                            className={errors.password ? styles.inputError : ""}
                                            required={!editingUser}
                                            placeholder={editingUser ? "Deixe em branco para manter" : ""}
                                        />
                                        {errors.password && <span className={styles.error}>{errors.password}</span>}
                                    </div>

                                    <div className={styles.formGroup}>
                                        <label htmlFor="confirmPassword">
                                            {editingUser ? "Confirmar Nova Senha" : "Confirmar Senha *"}
                                        </label>
                                        <input
                                            type="password"
                                            id="confirmPassword"
                                            value={confirmPassword}
                                            onChange={(e) => {
                                                setConfirmPassword(e.target.value);
                                                if (errors.confirmPassword) {
                                                    setErrors((prev) => {
                                                        const newErrors = { ...prev };
                                                        delete newErrors.confirmPassword;
                                                        return newErrors;
                                                    });
                                                }
                                            }}
                                            className={errors.confirmPassword ? styles.inputError : ""}
                                            required={!editingUser || !!formData.password}
                                        />
                                        {errors.confirmPassword && (
                                            <span className={styles.error}>{errors.confirmPassword}</span>
                                        )}
                                    </div>
                                </div>

                                <button type="submit" className={styles.submitButton}>
                                    {editingUser ? "Salvar Alterações" : "Registrar Usuário"}
                                </button>
                            </form>
                        </div>
                    </div>
                )}
            </main >
        </div >
    );
}
