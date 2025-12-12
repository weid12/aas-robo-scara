import { Box, Typography } from "@mui/material";
import aasLogo from "../../assets/aas-logo.png";
import styles from "./Loading.module.css";

export default function Loading({ message = "Carregando dados do robô SCARA..." }) {
    return (
        <Box
            sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                minHeight: "40vh",
                gap: 3,
            }}
        >
            <div className={styles.logoContainer}>
                <img src={aasLogo} alt="Loading" className={styles.logo} />
            </div>
            <Typography variant="body2" color="text.secondary">
                {message}
            </Typography>
        </Box>
    );
}
