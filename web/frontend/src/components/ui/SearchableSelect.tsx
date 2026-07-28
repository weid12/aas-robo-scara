import { useState, useRef, useEffect } from 'react';
import styles from './SearchableSelect.module.css';

interface Option {
    value: string;
    label: string;
}

interface SearchableSelectProps {
    options: Option[];
    value: string;
    onChange: (value: string) => void;
    placeholder?: string;
    className?: string;
}

export default function SearchableSelect({
    options,
    value,
    onChange,
    placeholder = 'Select an option',
    className = '',
}: SearchableSelectProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const containerRef = useRef<HTMLDivElement>(null);

    const selectedOption = options.find((opt) => opt.value === value);

    const filteredOptions = options.filter((option) =>
        option.label.toLowerCase().includes(searchTerm.toLowerCase())
    );

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false);
                setSearchTerm('');
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    const handleOptionClick = (optionValue: string) => {
        onChange(optionValue);
        setIsOpen(false);
        setSearchTerm('');
    };

    return (
        <div className={`${styles.searchableSelect} ${className}`} ref={containerRef}>
            <div
                className={styles.selectTrigger}
                onClick={() => setIsOpen(!isOpen)}
            >
                <span className={selectedOption ? styles.selectedValue : styles.placeholder}>
                    {selectedOption ? selectedOption.label : placeholder}
                </span>
                <svg
                    className={`${styles.arrow} ${isOpen ? styles.arrowUp : ''}`}
                    width="12"
                    height="12"
                    viewBox="0 0 12 12"
                    fill="none"
                >
                    <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.5" />
                </svg>
            </div>

            {isOpen && (
                <div className={styles.dropdown}>
                    <input
                        type="text"
                        className={styles.searchInput}
                        placeholder="Search..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        onClick={(e) => e.stopPropagation()}
                        autoFocus
                    />
                    <div className={styles.optionsList}>
                        {filteredOptions.length > 0 ? (
                            filteredOptions.map((option) => (
                                <div
                                    key={option.value}
                                    className={`${styles.option} ${option.value === value ? styles.optionSelected : ''
                                        }`}
                                    onClick={() => handleOptionClick(option.value)}
                                >
                                    {option.label}
                                </div>
                            ))
                        ) : (
                            <div className={styles.noResults}>No results found</div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
